import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import html2text

BASE_URL = "https://www.steelers.com/"
OUTPUT_DIR = "steelers_md"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 初始化 html 转 markdown 转换器
h = html2text.HTML2Text()
h.ignore_links = True  # 保留链接
h.ignore_images = True  # 不要图片
h.body_width = 0        # 不自动换行

def fetch_html(url):
    """获取网页 HTML"""
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"[ERROR] {url} 抓取失败: {e}")
        return None

def html_to_md(html):
    """HTML 转 Markdown"""
    return h.handle(html)

def save_markdown(url, md_text):
    """保存为 Markdown 文件"""
    parsed = urlparse(url)
    # 文件名：去掉域名，只保留路径
    path = parsed.path.strip("/")
    if not path:
        path = "index"
    filename = path.replace("/", "_") + ".md"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {url}\n\n")
        f.write(md_text)
    print(f"[OK] 保存 {filepath}")

def extract_nav_links(base_url, html):
    """提取子页面链接"""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # 只抓 Pirates 相关的页面
        if href.startswith("/pirates") or href.startswith(base_url):
            links.append(urljoin(base_url, href))
    return list(set(links))

def crawl(base_url):
    visited = set()
    to_visit = [base_url]

    while to_visit:
        url = to_visit.pop()
        if url in visited:
            continue
        visited.add(url)

        print(f"[CRAWL] {url}")
        html = fetch_html(url)
        if not html:
            continue

        # 转换成 markdown 并保存
        md_text = html_to_md(html)
        save_markdown(url, md_text)

        # 提取子页面
        links = extract_nav_links(base_url, html)
        for link in links:
            if link not in visited:
                to_visit.append(link)

    print(f"\n[DONE] 共抓取 {len(visited)} 个页面")

if __name__ == "__main__":
    crawl(BASE_URL)
