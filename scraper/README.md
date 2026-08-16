# The Polite Scraper

A scraping pipeline that downloads book data from a public practice sandbox, cleans it, validates it, and reports on the run — built to practice responsible, respectful scraping habits.

## Target classification

- **Site:** [Books to Scrape](https://books.toscrape.com/)
- **Why:** Books to Scrape is a public sandbox explicitly built so people can practice web scraping without ethical concerns — its own homepage states this directly.
- **Scope:** The first 3 catalogue pages only, and their 60 linked book detail pages.
- **Data collected:** Title, price, availability, star rating, description, and product URL for each book — all publicly displayed catalogue information, nothing behind a login or paywall.
- **Why this is appropriate:** The site exists specifically for scraping practice, requests only public catalogue data, and the volume (63 pages total) is small and respectful of the server.

**robots.txt result:** `https://books.toscrape.com/robots.txt` returns `404 Not Found` — no robots file found. A missing file is not permission on its own, but combined with the site's stated purpose as a practice sandbox, scraping here is appropriate.

I will not reuse this code on another site without checking its rules and terms first.

## How to run

```bash
cd scraper
python -m venv venv
venv\Scripts\Activate.ps1        # Windows
pip install requests beautifulsoup4 pydantic
python src/main.py
```

This single command discovers the first 3 catalogue pages, visits all 60 book detail pages, cleans and validates every record, and writes:

- `output/books.json` — 60 validated records
- `output/errors.json` — any records that failed validation
- `output/run-report.json` — a summary of the run

## Record schema

Each record in `books.json` has:

| Field | Type | Notes |
|---|---|---|
| `title` | string | |
| `product_url` | string | Absolute URL, used as the record's canonical identity |
| `price_text` | string | Original text as scraped, e.g. `£51.77` |
| `price_gbp` | number | Cleaned numeric price |
| `availability_text` | string | |
| `rating_text` | string or null | Word rating, e.g. `"Three"` |
| `description` | string or null | `null` when the book has no description on the page — never invented |
| `source_page` | string | Which catalogue page this book was discovered on |
| `fetched_at` | string | UTC ISO timestamp of when the detail page was fetched |

Records are validated against a Pydantic schema before being written. Any record that fails validation is written to `errors.json` with a reason instead of `books.json`.

## Politeness rules

- **User-agent:** every real request sends `FlyRankInternship-A9/1.0 (+link to this repo)`, identifying the scraper honestly.
- **Delay:** at least 500ms between real network requests. Cached reads skip the delay entirely.
- **Timeout:** every request gives up after 10 seconds rather than hanging forever.
- **Cache:** during development, pages are read from a local `cache/` folder instead of re-requesting the live site. `cache/` is git-ignored — it is never committed.
- **Retry rules:** timeouts and server errors (5xx) get one retry after a short pause. `404` and `403` responses are never retried.

## Why this assignment needed no browser

The data is already in the HTML the server sends, so a browser would only add cost.

## Sample run report

```json
{
  "start_time": "2026-08-16T22:57:19.319669+00:00",
  "duration_seconds": 1.700593,
  "pages_fetched": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1
}
```

## Honest limitation

This scraper is built specifically for Books to Scrape's exact HTML structure (CSS selectors like `article.product_pod`, `div.product_main`). It is not a general-purpose scraper and would need rework to target a different site.

## Ethics note

- Prefer an official API over scraping when one exists.
- Never bypass logins, paywalls, or explicit blocks (like a restrictive `robots.txt`).
- Collect only the data actually needed for the task, and be a polite, identifiable, rate-limited guest on someone else's server.