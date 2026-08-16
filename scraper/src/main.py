import os
import requests

BASE_URL = "https://books.toscrape.com/"
CACHE_DIR = "cache"
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/Martin-Nabil/flyrank-task-api)"
TIMEOUT_SECONDS = 10

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
    return html

if __name__ == "__main__":
    catalogue_url = BASE_URL + "catalogue/page-1.html"
    html = fetch_page(catalogue_url, "catalogue-page-1.html")