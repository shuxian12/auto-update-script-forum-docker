import argparse
import base64
import glob
import os
import re
import time
import json
import tqdm
from datetime import datetime

from azure.core.credentials import AzureKeyCredential
from azure.identity import AzureDeveloperCliCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    PrioritizedFields,
    SearchableField,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticSettings,
    SimpleField,
)
from azure.storage.blob import BlobServiceClient
from text_spliter import split_md

MAX_SECTION_LENGTH = 1000
MIN_SECTION_LENGTH = 376
# SENTENCE_SEARCH_LIMIT = 100
# SECTION_OVERLAP = 100

def blob_name_from_file_page(filename, page = 0):
    if os.path.splitext(filename)[1].lower() == ".pdf":
        return os.path.splitext(os.path.basename(filename))[0] + f"-{page}" + ".pdf"
    elif os.path.splitext(filename)[1].lower() == ".md":
        return os.path.splitext(os.path.basename(filename))[0] + f"-{page}" + ".md"
    else:
        return os.path.basename(filename)

def upload_blobs(filename):
    blob_service = BlobServiceClient(account_url=f"https://{args.storageaccount}.blob.core.windows.net", credential=storage_creds)
    blob_container = blob_service.get_container_client(args.container)
    if not blob_container.exists():
        blob_container.create_container()

    if filename.endswith(".md"):
        blob_name = os.path.basename(filename)
        with open(filename,"rb") as data:
            blob_container.upload_blob(blob_name, data, overwrite=True)

def remove_blobs(filename):
    if args.verbose: print(f"!! Removing blobs for '{filename or '<all>'}'")
    blob_service = BlobServiceClient(account_url=f"https://{args.storageaccount}.blob.core.windows.net", credential=storage_creds)
    blob_container = blob_service.get_container_client(args.container)
    if blob_container.exists():
        if filename == None:
            blobs = blob_container.list_blob_names()
        else:
            prefix = os.path.splitext(os.path.basename(filename))[0]
            blobs = filter(lambda b: re.match(f"{prefix}(-\d+)*\.md", b), blob_container.list_blob_names(name_starts_with=os.path.splitext(os.path.basename(prefix))[0]))
        count = 0
        for b in blobs:
            if args.verbose: print(f"\tRemoving blob {b}")
            blob_container.delete_blob(b)
            count += 1

        if count == 0:
            if args.verbose: print(f"\tNo blobs found, please check the filename or remove the file from the search index manually")

def get_document_text(filename: str, remove_img: bool, remove_href: bool) -> str | None:
    if filename.endswith(".md"):
        doc = open(filename, "r", encoding='utf-8').read()
        if len(doc) < MIN_SECTION_LENGTH:
            return None
        
        # Dealing with table spaces and dashes in markdown
        while doc.find('----') != -1:
            doc = doc.replace('----', '-')
        while doc.find('    ') != -1:
            doc = doc.replace('    ', ' ')
        while doc.find('   ') != -1:
            doc = doc.replace('   ', ' ')
        
        if remove_img:
            doc = re.sub(r"!\[.*\]\(.*\)", "", doc)
        if remove_href:
            doc = re.sub(r"\[(.*)\]\(.*\)", "\\1", doc)
        return doc
    else:
        raise Exception(f"File type not supported, {filename}")

def filename_to_id(filename):
    filename_ascii = re.sub("[^0-9a-zA-Z_-]", "_", filename)
    filename_hash = base64.b16encode(filename.encode('utf-8')).decode('ascii')
    return f"file-{filename_ascii}-{filename_hash}"

def create_sections(filename:str, page_map: str) -> dict:
    file_id = filename_to_id(filename)

    if filename.endswith(".md"):
        for i, doc in enumerate(split_md(page_map, filename)):
            try:
                section = {
                    "id": f"{file_id}-page-{i}",
                    "title": os.path.splitext(filename)[0],
                    "content": doc['content'],
                    "category": args.category,
                    "sourcepage": blob_name_from_file_page(filename, i),
                    "sourcefile": filename,
                    "headings": doc['heading'],# json.dumps(doc['heading'], ensure_ascii=False)
                    "markdown": doc['markdown'].replace('[toc]\n', '').replace('\n\n', '\n')
                }
                yield section
            except Exception as e:
                print(str(e))
    else:
        raise Exception(f"File type not supported, {filename}")

def create_search_index():
    if args.verbose: print(f"* Ensuring search index {args.index} exists")
    index_client = SearchIndexClient(endpoint=f"https://{args.searchservice}.search.windows.net/",
                                     credential=search_creds)
    if args.index not in index_client.list_index_names():
        index = SearchIndex(
            name=args.index,
            fields=[
                SimpleField(name="id", type="Edm.String", key=True),
                SearchableField(name="title", type="Edm.String", analyzer_name="en.microsoft"),
                SearchableField(name="content", type="Edm.String", analyzer_name="en.microsoft"),
                SimpleField(name="category", type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="sourcepage", type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="sourcefile", type="Edm.String", filterable=True, facetable=True),
                SearchableField(name="headings", type="Edm.String", analyzer_name="en.microsoft"),
                SimpleField(name="markdown", type="Edm.String", filterable=True, facetable=True)
            ],
            semantic_settings=SemanticSettings(
                configurations=[SemanticConfiguration(
                    name='default',
                    prioritized_fields=PrioritizedFields(
                        title_field=None, prioritized_content_fields=[SemanticField(field_name='content')]))])     
            )
        if args.verbose: print(f"+ Creating {args.index} search index")
        index_client.create_index(index)
    else:
        if args.verbose: print(f"* Search index {args.index} already exists")

def index_sections(filename, sections, bar: tqdm.tqdm):
    if args.verbose: bar.set_postfix_str(f"+ Indexing sections from '{filename}'")
    search_client = SearchClient(endpoint=f"https://{args.searchservice}.search.windows.net/",
                                 index_name=args.index,
                                 credential=search_creds)
    i = 0
    batch = []
    for s in sections:
        batch.append(s)
        i += 1
        if i % 1000 == 0:
            results = search_client.upload_documents(documents=batch)
            succeeded = sum([1 for r in results if r.succeeded])
            if args.verbose and len(results) != succeeded: bar.set_postfix_str(f"{filename}: Indexed {len(results)} sections, {succeeded} succeeded")
            batch = []

    if len(batch) > 0:
        results = search_client.upload_documents(documents=batch)
        succeeded = sum([1 for r in results if r.succeeded])
        if args.verbose and len(results) != succeeded: bar.set_postfix_str(f"{filename}: Indexed {len(results)} sections, {succeeded} succeeded")

def remove_from_index(filename):
    if args.verbose: bar.set_postfix_str(f"!! Removing sections from '{filename or '<all>'}' from search index '{args.index}'")
    search_client = SearchClient(endpoint=f"https://{args.searchservice}.search.windows.net/",
                                    index_name=args.index,
                                    credential=search_creds)
    while True:
        filter = None if filename == None else f"sourcefile eq '{os.path.basename(filename)}'"
        r = search_client.search("", filter=filter, top=1000, include_total_count=True)
        if r.get_count() == 0:
            if args.verbose: bar.set_postfix_str(f"\tNo more sections found in index")
            break
        r = search_client.delete_documents(documents=[{ "id": d["id"] } for d in r])
        if args.verbose: bar.set_postfix_str(f"\tRemoved {len(r)} sections from index")
        # It can take a few seconds for search results to reflect changes, so wait a bit
        time.sleep(2)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Prepare documents by extracting content from Markdowns, splitting content into sections, uploading to blob storage(optional), and indexing in a search index.",
        epilog="Example 1: prepdocs.py '../data/*.md' --storageaccount myaccount --container mycontainer --searchservice mysearch --index myindex -v\nExample 2: prepdocs.py '../md/*' --searchservice 'mysearch' --index 'myindex' --tenantid 'mytenantid' --searchkey 'mysearchkey' --skipblobs --remove_image -v"
        )
    parser.add_argument("files", help="Files to be processed")
    parser.add_argument("--category", help="Value for the category field in the search index for all sections indexed in this run")
    parser.add_argument("--skipblobs", action="store_true", help="Skip uploading individual pages to Azure Blob Storage")
    parser.add_argument("--storageaccount", required=False, help="Optional. Azure Blob Storage account name. (If skipblobs, this is not required)")
    parser.add_argument("--container", required=False, help="Optional. Azure Blob Storage container name. (If skipblobs, this is not required)")
    parser.add_argument("--storagekey", required=False, help="Optional. Use this Azure Blob Storage account key instead of the current user identity to login (use az login to set current user for Azure) (If skipblobs, this is not required)")
    parser.add_argument("--tenantid", required=False, help="Optional. Use this to define the Azure directory where to authenticate)")
    parser.add_argument("--searchservice", help="Name of the Azure Cognitive Search service where content should be indexed (must exist already)")
    parser.add_argument("--index", help="Name of the Azure Cognitive Search index where content should be indexed (will be created if it doesn't exist)")
    parser.add_argument("--searchkey", required=False, help="Optional. Use this Azure Cognitive Search account key instead of the current user identity to login (use az login to set current user for Azure)")
    parser.add_argument("--remove", action="store_true", help="Remove references to this document from blob storage and the search index")
    parser.add_argument("--removeall", action="store_true", help="Remove all blobs from blob storage and documents from the search index")
    parser.add_argument("--remove_index", action="store_true", help="Remove references to this document from the search index")
    parser.add_argument("--remove_blobs", action="store_true", help="Remove references to this document from blob storage")
    parser.add_argument("--remove_image", action="store_true", help="Remove images from this document in search index")
    parser.add_argument("--remove_href", action="store_true", help="Remove hrefs from this document in search index")
    parser.add_argument("--test", action="store_true", help="Test mode, don't actually upload or index anything, instead save the index in the local file in test folder")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # for k, v in vars(args).items():
    #     print(f"{k}: {v}")
    # Use the current user identity to connect to Azure services unless a key is explicitly set for any of them
    azd_credential = AzureDeveloperCliCredential() if args.tenantid == None else AzureDeveloperCliCredential(tenant_id=args.tenantid, process_timeout=60)
    default_creds = azd_credential if args.searchkey == None or args.storagekey == None else None
    search_creds = default_creds if args.searchkey == None else AzureKeyCredential(args.searchkey.strip())
    # print(args.searchkey, search_creds)

    # check folder
    old_file_path_list = [f for f in os.listdir(args.files) if os.path.isdir(os.path.join(args.files, f))]
    old_file_path_list = [datetime.strptime(os.path.basename(f), '%Y-%m-%d_%H,%M,%S') for f in old_file_path_list]
    old_file_path_list.sort()
    latest_updated_folder = old_file_path_list[-1].strftime('%Y-%m-%d_%H,%M,%S')
    print(f"* Latest updated folder: {latest_updated_folder}")
    files = [os.path.join(args.files, latest_updated_folder, "new/data/*.md"), os.path.join(args.files, latest_updated_folder, "update/data/*.md")]

    if not args.skipblobs:
        storage_creds = default_creds if args.storagekey == None else args.storagekey

    if args.test:
        if not os.path.exists("test"):
            os.mkdir("test")

    if args.removeall:
        remove_blobs(None)
        remove_from_index(None)
        exit(0)

    if not args.remove:
        create_search_index()
    
    t = sum([len(glob.glob(f)) for f in files])
    if args.verbose: print(f"* Total have {t} files to process")

    print(f"* Processing ...")
    short, total = 0, 0
    for folder in files:
        # file_list = [f for f in glob.glob(folder) if 'Release_note' not in f] # remove Release_note
        file_list = glob.glob(folder)
        folder_file_sum = len(file_list)
        total += folder_file_sum

        print(f"* Processing folder: {('/').join(folder.split('/')[-3:])}, total files: {folder_file_sum}")
        if folder_file_sum == 0:
            print(f"- Folder {folder} is empty")
            continue

        for filename in (bar := tqdm.tqdm(file_list, bar_format='{l_bar}{bar:30}{r_bar}{bar:-10b}')):
            # if args.verbose: print(f"Processing '{filename}'")
            if args.remove:
                remove_blobs(filename)
                remove_from_index(filename)
            elif args.remove_index:
                remove_from_index(filename)
            elif args.remove_blobs:
                remove_blobs(filename)
            else:
                page_map = get_document_text(filename, args.remove_image, args.remove_href)
                if page_map == None:
                    short += 1
                    if args.verbose: print(f"\tSkipping short document '{('/').join(filename.split('/')[-4:])}'")
                    continue
                sections = create_sections(os.path.basename(filename), page_map)

                if args.test:
                    if not os.path.exists("test"):  os.mkdir("test")
                    with open(f'test/md_{filename.split("/")[-1].split(".")[0]}.json', 'w', encoding='utf-8') as f:
                        f.write(json.dumps([s for s in sections], indent=4, ensure_ascii=False))    
                else:
                    index_sections(os.path.basename(filename), sections, bar)
                    if not args.skipblobs:
                        upload_blobs(filename)

    if args.verbose: print(f"* Done, {short} short documents skipped, and {total} files processed")