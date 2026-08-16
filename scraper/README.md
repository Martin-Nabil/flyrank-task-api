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