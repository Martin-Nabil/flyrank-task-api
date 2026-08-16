import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://books.toscrape.com/"
CACHE_DIR = "cache"
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/Martin-Nabil/flyrank-task-api)"
TIMEOUT_SECONDS = 10
DELAY_SECONDS = 0.5

def fetch_page(url: str, cache_filename: str) -> str:
    """Fetch a page, using a local cache if it already exists."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            html = f.read()
        print(f"CACHE HIT: {cache_filename} ({len(html)} bytes)")
        return html

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)

    if response.status_code != 200:
        raise RuntimeError(f"FETCH FAILED: {url} returned status {response.status_code}")

    html = response.text
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"FETCH: {cache_filename} ({len(html)} bytes)")
    time.sleep(DELAY_SECONDS)
    return html

def discover_book_urls():
    """Visit the first 3 catalogue pages and collect every unique book URL."""
    all_book_urls = []
    page_url = BASE_URL + "catalogue/page-1.html"
    page_num = 1

    while page_url and page_num <= 3:
        cache_filename = f"catalogue-page-{page_num}.html"
        html = fetch_page(page_url, cache_filename)
        soup = BeautifulSoup(html, "html.parser")

        for article in soup.select("article.product_pod"):
            link = article.select_one("h3 a")
            if link and link.get("href"):
                absolute_url = urljoin(page_url, link["href"])
                all_book_urls.append(absolute_url)

        next_link = soup.select_one("li.next a")
        if next_link and next_link.get("href"):
            page_url = urljoin(page_url, next_link["href"])
            page_num += 1
        else:
            page_url = None

    unique_urls = list(dict.fromkeys(all_book_urls))

    print(f"catalogue_pages={min(page_num, 3)}")
    print(f"discovered={len(all_book_urls)}")
    print(f"unique_urls={len(unique_urls)}")

    return unique_urls

if __name__ == "__main__":
    book_urls = discover_book_urls()