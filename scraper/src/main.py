import os
import time
import re
import json
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pydantic import BaseModel, ValidationError

BASE_URL = "https://books.toscrape.com/"
CACHE_DIR = "cache"
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/Martin-Nabil/flyrank-task-api)"
TIMEOUT_SECONDS = 10
DELAY_SECONDS = 0.5

STATS = {"cache_hits": 0, "pages_fetched": 0, "failed_pages": 0}

def fetch_page(url: str, cache_filename: str, allow_retry: bool = True) -> str | None:
    """Fetch a page, using a local cache if it already exists. Returns None on failure."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            html = f.read()
        print(f"CACHE HIT: {cache_filename} ({len(html)} bytes)")
        STATS["cache_hits"] += 1
        return html

    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
    except requests.exceptions.RequestException as e:
        if allow_retry:
            print(f"FETCH FAILED (after retry): {url} â€” {e}")
            time.sleep(1)
            return fetch_page(url, cache_filename, allow_retry=False)
        print(f"FETCH FAILED (after retry): {url} — {e}")
        STATS["failed_pages"] += 1
        return None

    if response.status_code == 200:
        response.encoding = "utf-8"
        html = response.text

        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"FETCH: {cache_filename} ({len(html)} bytes)")
        STATS["pages_fetched"] += 1
        time.sleep(DELAY_SECONDS)
        return html

    if response.status_code >= 500 and allow_retry:
        print(f"FETCH FAILED (status {response.status_code}, retrying once): {url}")
        time.sleep(1)
        return fetch_page(url, cache_filename, allow_retry=False)

    print(f"FETCH FAILED (status {response.status_code}, not retrying): {url}")
    STATS["failed_pages"] += 1
    return None

def discover_book_urls():
    """Visit the first 3 catalogue pages and collect every unique book URL with its source page."""
    all_books = []
    seen_urls = set()
    page_url = BASE_URL + "catalogue/page-1.html"
    page_num = 1

    while page_url and page_num <= 3:
        cache_filename = f"catalogue-page-{page_num}.html"
        html = fetch_page(page_url, cache_filename)
        if html is None:
            break
        soup = BeautifulSoup(html, "html.parser")

        for article in soup.select("article.product_pod"):
            link = article.select_one("h3 a")
            if link and link.get("href"):
                absolute_url = urljoin(page_url, link["href"])
                if absolute_url not in seen_urls:
                    seen_urls.add(absolute_url)
                    all_books.append({"url": absolute_url, "source_page": page_url})

        next_link = soup.select_one("li.next a")
        if next_link and next_link.get("href"):
            page_url = urljoin(page_url, next_link["href"])
            page_num += 1
        else:
            page_url = None

    print(f"catalogue_pages={min(page_num, 3)}")
    print(f"discovered={len(all_books)}")
    print(f"unique_urls={len(seen_urls)}")

    return all_books
def extract_book(book_url: str, source_page: str) -> dict | None:
    """Fetch one book detail page and extract the 8 raw fields. Returns None if the page failed."""
    cache_filename = re.sub(r"[^a-zA-Z0-9]+", "_", book_url) + ".html"
    html = fetch_page(book_url, cache_filename)
    if html is None:
        return None
    soup = BeautifulSoup(html, "html.parser")

    product_main = soup.select_one("div.product_main")

    title = product_main.select_one("h1").get_text(strip=True)

    price_text = product_main.select_one("p.price_color").get_text(strip=True)

    availability_text = product_main.select_one("p.availability").get_text(strip=True)

    rating_tag = product_main.select_one("p.star-rating")
    rating_classes = rating_tag.get("class", [])
    rating_text = next((c for c in rating_classes if c != "star-rating"), None)

    description_tag = soup.select_one("#product_description ~ p")
    description = description_tag.get_text(strip=True) if description_tag else None

    return {
        "title": title,
        "product_url": book_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }

class Book(BaseModel):
    title: str
    product_url: str
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str | None = None
    description: str | None = None
    source_page: str
    fetched_at: str

def normalize_record(raw: dict) -> dict:
    """Turn raw extracted text into clean typed values."""
    clean = dict(raw)

    price_match = re.search(r"[\d.]+", raw["price_text"])
    clean["price_gbp"] = float(price_match.group()) if price_match else None

    return clean

def validate_and_store(raw_records: list[dict]):
    """Normalize, validate, and split records into good and bad."""
    good_records = []
    error_records = []
    seen_urls = set()

    for raw in raw_records:
        normalized = normalize_record(raw)

        if normalized["product_url"] in seen_urls:
            continue
        seen_urls.add(normalized["product_url"])

        try:
            book = Book(**normalized)
            good_records.append(book.model_dump())
        except ValidationError as e:
            error_records.append({
                "product_url": raw.get("product_url", "unknown"),
                "reason": str(e)
            })

    os.makedirs("output", exist_ok=True)
    with open("output/books.json", "w", encoding="utf-8") as f:
        json.dump(good_records, f, indent=2, ensure_ascii=False)

    with open("output/errors.json", "w", encoding="utf-8") as f:
        json.dump(error_records, f, indent=2, ensure_ascii=False)

    print(f"valid_records={len(good_records)}")
    print(f"invalid_records={len(error_records)}")

    return good_records, error_records

if __name__ == "__main__":
    start_time = datetime.now(timezone.utc)

    books = discover_book_urls()

    # Deliberately broken URL to prove the pipeline survives a bad page
    books.append({
        "url": BASE_URL + "catalogue/this-book-does-not-exist_00000/index.html",
        "source_page": BASE_URL + "catalogue/page-1.html"
    })

    records = []
    for book in books:
        record = extract_book(book["url"], source_page=book["source_page"])
        if record is not None:
            records.append(record)

    print(f"detail_pages={len(records)}")

    good_records, error_records = validate_and_store(records)

    end_time = datetime.now(timezone.utc)
    duration_seconds = (end_time - start_time).total_seconds()

    run_report = {
        "start_time": start_time.isoformat(),
        "duration_seconds": duration_seconds,
        "pages_fetched": STATS["pages_fetched"],
        "cache_hits": STATS["cache_hits"],
        "valid_records": len(good_records),
        "invalid_records": len(error_records),
        "failed_pages": STATS["failed_pages"]
    }

    with open("output/run-report.json", "w", encoding="utf-8") as f:
        json.dump(run_report, f, indent=2)

    print(json.dumps(run_report, indent=2))