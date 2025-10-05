import requests
from bs4 import BeautifulSoup
import os
import html2text
from urllib.parse import urljoin, urlparse

BASE_URL = "https://www.visitpittsburgh.com"
START_URL = "https://www.visitpittsburgh.com/things-to-do/pittsburgh-sports-teams/"
SAVE_DIR = "pittsburgh_sports_md"
os.makedirs(SAVE_DIR, exist_ok=True)

def get_page(url):
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.text

def extract_links(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(base_url, href)  # 处理相对路径
        # 限制在本站点
        if urlparse(full_url).netloc == urlparse(BASE_URL).netloc:
            links.append(full_url)
    return list(set(links))

def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup
    h = html2text.HTML2Text()
    h.ignore_links = True  # 忽略链接
    h.ignore_images = True  # 忽略图片
    h.body_width = 0  # 不限制行宽
    text = h.handle(str(main))
    return text

# 抓取入口页
html = get_page(START_URL)
links = extract_links(html, START_URL)

# 把入口页也放进去
all_pages = [START_URL] + links

# 遍历抓取
for url in all_pages:
    print("Processing:", url)
    page_html = get_page(url)
    text = extract_text(page_html)

    # 生成文件名
    parts = [p for p in url.split("/") if p]
    filename = parts[-1] if parts[-1] != "sports-teams" else "index"
    filename += ".md"

    with open(os.path.join(SAVE_DIR, filename), "w", encoding="utf-8") as f:
        f.write(text)

print("✅ 抓取完成，文件保存在:", SAVE_DIR)
