import requests
from bs4 import BeautifulSoup
import os
import html2text
from urllib.parse import urljoin, urlparse
import time

# 基本配置
BASE_DOMAIN = "nhl.com"
START_URL = "https://www.nhl.com/penguins/"
SAVE_DIR = "nhl_penguins_md"
os.makedirs(SAVE_DIR, exist_ok=True)

# 限制参数
MAX_PAGES = 50            # 最多爬多少页
MAX_DEPTH = 2             # 最多递归深度（起始页面 depth = 0）
DELAY = 1.0               # 每请求之间的延迟（秒）
ALLOWED_PATH_PREFIXES = ["/pirates"]  # 只爬这些路径下的链接

# 工具函数
def get_page(url):
    print("GET", url)
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.text

def extract_links(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        # 同域限制
        if parsed.netloc.endswith(BASE_DOMAIN):
            # 路径是否在允许爬取的前缀中？
            for pref in ALLOWED_PATH_PREFIXES:
                if parsed.path.startswith(pref):
                    links.append(full)
                    break
    return links

def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")
    # 尽量选正文容器，这里先尝试 <main>
    main = soup.find("main")
    if main:
        block = main
    else:
        block = soup.body or soup
    h = html2text.HTML2Text()
    h.ignore_links = True  # 忽略链接
    h.ignore_images = True  # 忽略图片
    text = h.handle(str(block))
    return text

def safe_filename_from_url(url):
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if path == "":
        fname = "index"
    else:
        # 把斜杠除掉，用下划线替代
        fname = path.replace("/", "_")
    return fname + ".md"

def crawl(start_url):
    visited = set()
    to_visit = [(start_url, 0)]  # tuple(url, depth)
    count = 0

    while to_visit and count < MAX_PAGES:
        url, depth = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            html = get_page(url)
        except Exception as e:
            print("Failed to fetch:", url, e)
            continue

        text = extract_text(html)
        fname = safe_filename_from_url(url)
        outpath = os.path.join(SAVE_DIR, fname)
        with open(outpath, "w", encoding="utf-8") as f:
            f.write(text)

        count += 1

        # 深度控制
        if depth < MAX_DEPTH:
            links = extract_links(html, url)
            for link in links:
                if link not in visited:
                    to_visit.append((link, depth + 1))

        time.sleep(DELAY)

    print("Crawled pages:", len(visited))
    print("Saved files in:", SAVE_DIR)

if __name__ == "__main__":
    crawl(START_URL)
