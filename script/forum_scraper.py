import requests, re, tqdm, os, pdfkit
from bs4 import BeautifulSoup, Comment
from markdownify import markdownify as md
UTF_8 = '<meta http-equiv="Content-type" content="text/html; charset=utf-8" />\n'

# change the forum url here
ROOT_URL = "https://forum.aim-linux.advantech.com/categories"

def download(root=ROOT_URL, target_path='.'):
    esponse = requests.get(root)
    soup = BeautifulSoup(response.content, 'html.parser')

    category_lst = find_category(soup)
    topic_lst = find_post_url(category_lst)

    for post in tqdm.tqdm(topic_lst):
        convert_to_md(post, target_path)

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

def convert_to_md(url, path='./data'):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    title = soup.find('h1').text.strip().replace(' ', '_').replace('/', '_').replace('?', '').replace(':', '_').replace('|', '_').replace('"', '').replace('<', '_').replace('>', '_').replace('*', '_').replace(',', '_')
    file_name = f'{path}/{title}'
    comment = Comment(url)
    soup.insert(-1, comment)
    with open(file_name + '.html', 'w', encoding='utf-8') as f:
        f.write(UTF_8 + str(soup))

    try:
        pdfkit.from_string(UTF_8 + str(soup), file_name + '.pdf')
    except:
        print(f'pdfkit error: {file_name}, {url}')
        open(f'{TARGET_PATH}error_pdfkit.txt', 'a+', encoding='utf-8').write(f'{"update/" if not add else "new/"}data/{file_name} || {url}\n')

    # docs = []
    post_list = soup.find_all('div', class_='topic-body crawler-post')
    s = BeautifulSoup()

    n = post_list[0].find('span', itemprop='name')
    n.replace_with(f"{n.text.strip()} (Question): ")
    n.name = 'b'
    # idx = post_list[0].find('span', itemprop='position')
    c = post_list[0].find('div', class_='post', itemprop='articleBody')
    # docs.append({'name': n.text.strip(), 'idx': (int)(idx.text.strip()), 'content': c.text.strip()})
    s.extend([n, c])

    for post in post_list[1:]:
        n = post.find('span', itemprop='name')
        n.name = 'b'
        n.replace_with(f"{n.text.strip()} (Reply): ")
        # idx = post.find('span', itemprop='position')
        c = post.find('div', class_='post', itemprop='text')
        # docs.append({'name': n.text.strip(), 'idx': (int)(idx.text.strip()), 'content': c.text.strip()})
        s.extend([n, c])

    # docs.sort(key=lambda x: x['idx'])
    with open(f'./data/{title}.md', 'w', encoding='utf-8') as f:
        content = md(str(s))
        content = re.sub(r'(?<!\n)\n\n+', '\n', content)
        f.write(content)
    

if __name__ == '__main__':
    if not os.path.exists('./data'):
        os.mkdir('./data')
    download()