# %%
import requests, re, os, pdfkit, markdownify, argparse, sys, json, hashlib, shutil, tqdm
from bs4 import BeautifulSoup, Comment
from datetime import datetime

UTF_8 = '<meta http-equiv="Content-type" content="text/html; charset=utf-8" />\n'
DOMAIN = "https://forum.aim-linux.advantech.com"

num, up = 0, 0
pre_url = ''
pre_queue = set()
pdf_links = set()

def convert_md(soup: BeautifulSoup):
    post_list = soup.find_all('div', class_='topic-body crawler-post')
    s = BeautifulSoup()

    n = post_list[0].find('span', itemprop='name')
    n.string = f"{n.text.strip()} (Question): "
    n.name = 'b'
    # idx = post_list[0].find('span', itemprop='position')
    c = post_list[0].find('div', class_='post', itemprop='articleBody')
    # docs.append({'name': n.text.strip(), 'idx': (int)(idx.text.strip()), 'content': c.text.strip()})
    s.extend([n, c])

    for post in post_list[1:]:
        n = post.find('span', itemprop='name')
        n.name = 'b'
        n.string = f"{n.text.strip()} (Reply): "
        # idx = post.find('span', itemprop='position')
        c = post.find('div', class_='post', itemprop='text')
        # docs.append({'name': n.text.strip(), 'idx': (int)(idx.text.strip()), 'content': c.text.strip()})
        s.extend([n, c])
    
    content = markdownify.markdownify(str(s), heading_style='ATX')
    content = re.sub(r'(?<!\n)\n\n+', '\n', content)
    return content

def store_webpage(url: str, html: BeautifulSoup, file_name: str, add: bool = False):
    path = f'{TARGET_PATH}{"update/" if not add else "new/"}data/'
    if not os.path.exists(path):
        os.mkdir(path)

    open(path + file_name + '.html', 'w', encoding='utf-8').write(UTF_8 + str(html))
    open(path + file_name + '.md', 'w', encoding='utf-8').write(convert_md(html))
    try:
        pdfkit.from_string(UTF_8 + str(html), path + file_name + '.pdf')
    except:
        print(f'!! pdfkit error: {file_name}, {url}')
        open(f'{TARGET_PATH}error_pdfkit.txt', 'a+', encoding='utf-8').write(f'{"update/" if not add else "new/"}data/{file_name} || {url}\n')
    return

def download_or_update(url: str, html: BeautifulSoup, file_name: str):
    # check update and write to site_change.json
    origin_hash = hash_list[file_name] if file_name in hash_list else None
    new_hash = hashlib.md5((UTF_8 + str(html)).encode('utf-8')).hexdigest()

    if not origin_hash:
        if UPDATE: print(f' ====== {file_name} is a new file ======')
        hash_list[file_name] = new_hash
        store_webpage(url, html, file_name, add=True)
    elif origin_hash != new_hash:
        if UPDATE: print(f' ====== {file_name} has been updated ======')
        hash_list[file_name] = new_hash
        store_webpage(url, html, file_name)
    return

def find_category(soup):
    category_lst = set()
    infos = soup.find_all('a')
    for info in infos:
        if 'href' in info.attrs:
            if '/c/' in info['href'] and 'news-announcements' not in info['href'] and 'simplified-chinese' not in info['href'] and 'traditional-chinese' not in info['href']:
                category_lst.add("https://forum.aim-linux.advantech.com" + info['href'])
    return category_lst

def find_post_url(category_lst):
    topic_lst = set()
    for category in category_lst:
        response = requests.get(category)
        soup = BeautifulSoup(response.content, 'html.parser')
        infos = soup.find_all('a')
        for info in infos:
            if 'href' in info.attrs:
                if '/t/' in info['href']:
                    topic_lst.add(info['href'])
    return topic_lst

def download(root: str):
    response = requests.get(root)
    soup = BeautifulSoup(response.content, 'html.parser')

    category_lst = find_category(soup)
    topic_lst = find_post_url(category_lst)

    for post in tqdm.tqdm(topic_lst):
        download_page(post)

def download_page(url: str):
    global num, pre_url

    if url == pre_url:
        return
    if url in pre_queue or url in pdf_links:
        return

    pre_queue.add(url)
    pre_url = url

    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, 'html.parser')

        # file name
        file_name = soup.find('h1').text.strip().replace(' ', '_').replace('/', '_').replace(':', '_').replace('\\', '_').replace('?', '_').replace('&', '_').replace(',', '_')
        
        if '對於分類：' in file_name or 'About' in file_name and 'category' in file_name:
            return

        comment = Comment(f' {url} ')
        link = soup.new_tag('a', href=url)
        link.string = 'Retrieve URL'
        soup.insert(-1, link)
        soup.insert(-1, comment)
        
        download_or_update(url, soup, file_name)
        num += 1

    except Exception as e:
        print(f' ====== error: {url} ======\n\t{e}')
        open(f'{TARGET_PATH}error.txt', 'a+', encoding='utf-8').write(url + '\n')
        pass

# 檢查資料夾是否完整
def create_upcoming_folder():
    print(f'+ Create empty folder: {TARGET_PATH}')
    os.mkdir(f'{TARGET_PATH}')
    os.mkdir(f'{TARGET_PATH}origin')
    os.mkdir(f'{TARGET_PATH}origin/data')
    os.mkdir(f'{TARGET_PATH}update')
    os.mkdir(f'{TARGET_PATH}new')
    for file in ['error.txt', 'error_pdfkit.txt']:
        open(f'{TARGET_PATH}{file}', 'w', encoding='utf-8').write('')
    open(f'{TARGET_PATH}site_change.json', 'w', encoding='utf-8').write('{}')
    

def new_check():
    if not os.path.exists(ROOT_FOLDER):
        raise FileNotFoundError(f'Folder: {ROOT_FOLDER} doesn\'t exist, please check the path.')
    else:
        # check if the folder update is empty
        if os.listdir(ROOT_FOLDER):
            delete_check = input(f'> Folder {ROOT_FOLDER} is not empty, Would you like to delete all files in this folder, and continue downloading? (y/n):')
            while delete_check not in ['y', 'n']:
                delete_check = input(f'> Please enter y or n: ')

            if delete_check == 'y':
                print(f'!! Delete files in folder: {ROOT_FOLDER}')
                shutil.rmtree(ROOT_FOLDER)
                os.mkdir(ROOT_FOLDER)
            else:
                print(f'!! Please delete all files in {ROOT_FOLDER} manually before creating a new folder.')
                sys.exit(0)

        # create upcoming folder
        create_upcoming_folder()

        open(f'{ROOT_FOLDER}url.txt', 'w', encoding='utf-8').write(URL)
    return

def check_if_folder_in_folder(file_name: str):
    for folder in ['origin', 'update', 'new']:
        if not os.path.exists(f'{file_name}{folder}'):
            print(f'!! Folder: {file_name}{folder} doesn\'t exist.')
            return False
    return True

def update_check():
    if not os.listdir(ROOT_FOLDER):
        raise FileNotFoundError(f'Folder: {ROOT_FOLDER} is empty, please check the path or we can\'t update.')
    elif open(f'{ROOT_FOLDER}url.txt', 'r', encoding='utf-8').read() != URL:
        raise ValueError(f'Folder: {ROOT_FOLDER} is not the folder of {URL}, please check the path.')
    else:
        old_file_path_list = [f for f in os.listdir(ROOT_FOLDER) if os.path.isdir(os.path.join(ROOT_FOLDER, f))]
        old_file_path_list = [datetime.strptime(os.path.basename(f), '%Y-%m-%d_%H,%M,%S') for f in old_file_path_list]
        old_file_path_list.sort()
        latest_updated_folder = old_file_path_list[-1].strftime('%Y-%m-%d_%H,%M,%S')
        print(f'* Latest updated folder: {latest_updated_folder}')
        
        if not check_if_folder_in_folder(ROOT_FOLDER + latest_updated_folder + '/'):
            raise FileNotFoundError(f'Folder: {ROOT_FOLDER}{latest_updated_folder}/ is not complete, please check the folder.')

        create_upcoming_folder()
        # copy latest updated data to new folder
        print(f'+ Copy latest updated data to new folder {TARGET_PATH}origin/.')
        for folder in ['origin', 'update', 'new']:
            old_path = f'{ROOT_FOLDER}{latest_updated_folder}/{folder}/data/'
            if not os.path.exists(old_path):    
                # print(f'! Folder: {old_path} doesn\'t exist.')
                continue
            datas = os.listdir(old_path)

            for data in datas:
                shutil.copy(old_path + data, f'{TARGET_PATH}origin/data/')
        # copy site_change.json to new folder
        shutil.copy(f'{ROOT_FOLDER}{latest_updated_folder}/site_change.json', f'{TARGET_PATH}site_change.json')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description="Download Advanteck wiki page recursively, according to the url you give.",
        epilog="> Ex: python download_wiki.py --folder 'download_wiki/' --new"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    parser.add_argument('--url', type=str, required=False, help='The root url you want to download from Advantech wiki')
    parser.add_argument('--folder', type=str, required=True, help='The folder where you want to save files.')
    group.add_argument('-n', '--new', action='store_true', help='Create a new folder to save files and create a new site_change.json file')
    group.add_argument('-u', '--update', action='store_true', help='Check if there is any update in the wiki page, and update the site_change.json file.\nNew or changed files will be saved in FOLDER/update/, you should update the indexes in FOLDER/update/ by using upload_index/prepdocs.py')
    args = parser.parse_args()

    # check file_path
    ROOT_FOLDER = args.folder + '/' if not args.folder.endswith('/') else args.folder
    TARGET_PATH = f'{ROOT_FOLDER}{datetime.now().strftime("%Y-%m-%d_%H,%M,%S")}/'
    UPDATE = args.update
    NEW = args.new
    URL = "https://forum.aim-linux.advantech.com/categories" if not args.url else args.url

    if NEW:
        new_check()
    elif UPDATE:
        update_check()

    hash_list = json.load(open(f'{TARGET_PATH}site_change.json', 'r', encoding='utf-8'))
    if UPDATE: print(f'* Original folder has {len(hash_list)} files.')

    print(f'+ Start crawling from {URL}')
    download(URL)

    open(f'{TARGET_PATH}site_change.json', 'w', encoding='utf-8').write(json.dumps(hash_list, ensure_ascii=False, indent=4))

    if UPDATE:
        print(f'* Total {int(len(os.listdir(f"{TARGET_PATH}update/data/"))/3) if os.path.exists(f"{TARGET_PATH}update/data/") else 0} articles have been updated.')
        print(f'* Total {int(len(os.listdir(f"{TARGET_PATH}new/data/"))/3) if os.path.exists(f"{TARGET_PATH}new/data/") else 0} articles has been added.')
    else:
        print(f'* Total {num} articles have been crawled.')
        print(f'* {len(open(f"{TARGET_PATH}error.txt", "r", encoding="utf-8").read().splitlines())} articles were failed to crawl.')
        print(f'* PDF convertion ERROR {len(open(f"{TARGET_PATH}error_pdfkit.txt", "r", encoding="utf-8").read().splitlines())} articles.')
    print('====== Completion ======')
    
# %%
"""
!!!!!!!!! Warning !!!!!!!!!
在使用前，請先前往markdownify.markdownify的source code.
1. 在convert_a(self, el, text, convert_as_inline)的return前，加上href的判斷式，如下:
    if text.strip()[0] == '!':  href = False    # 如果是圖片，就不要加上href
   因為有些圖片的<img>還會再用<a>包起來，這樣會造成圖片的連結失效

如果其他的東西還有問題的話，請參考以下:
1. 請將chomp(text)中約第38行的 text = text.strip() 改為 text = text.replace("\n", " ").strip()
2. 將convert_hn(self, n, el, text, convert_as_inline)中約第 269 行中的 text = text.rstrip() 改為 text = text.replace('\n', ' ')

====================

Before using, please visit the source code of markdownify.markdownify.

1. Add the following conditional statement, before the "return"(around 231th line) in "convert_a(self, el, text, convert_as_inline)"(around 216th line):

    ```python
    if text.strip()[0] == '!':  href = False  # Exclude href if it's an image
    return '%s[%s](%s%s)%s' % (prefix, text, href, title_part, suffix) if href else text
    ```
   This is necessary as some images are enclosed within an `<a>` tag, which causes the image links to break.

If you encounter other issues, please refer to the following:

1. In the `chomp(text)` function, modify the line around the 38th line from `text = text.strip()` to `text = text.replace("\\n", " ").strip()`.
2. In the `convert_hn(self, n, el, text, convert_as_inline)` function, adjust the line around the 269th line from `text = text.rstrip()` to `text = text.replace('\\n', ' ')`.
"""