# PDF Report Generator

Generates a PDF summary report of the scraped book catalogue as a background job — the same accept-fast/work-in-background/report-status pattern from the background-jobs project, applied to report generation instead of an LLM call.

Builds directly on `background-jobs/` — same job/worker/status shape, reused here for a different kind of slow work: querying + aggregating data and rendering a PDF, instead of calling a model.

## Try it

```bash
# Kick off report generation — returns instantly
curl -X POST http://localhost:8003/reports
```

Response (immediate):
```json
{"report_id":"...","status":"pending"}
```

```bash
# Check status
curl http://localhost:8003/reports/<report_id>
```

Response (once ready):
```json
{
  "report_id": "...",
  "status": "completed",
  "download_url": "/reports/<report_id>/download",
  "error": null,
  "attempts": 1,
  "created_at": "...",
  "updated_at": "..."
}
```

```bash
# Download the actual PDF
curl -o report.pdf http://localhost:8003/reports/<report_id>/download
```

A sample generated report is included at [`output/sample-report.pdf`](output/sample-report.pdf).

## How to run

```bash
cd pdf-reports
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Terminal 1 — the API
uvicorn src.main:app --reload --port 8003

# Terminal 2 — the worker (separate process, polls for report jobs)
python src/worker.py
```

Requires `books.json` in the project root — a sample is included, sourced from the Week 5 scraper's output.

## The pattern

- **`POST /reports`** stores a job as `pending` and returns `202` instantly — no rendering happens on this request.
- **The worker** (`src/worker.py`) polls for pending reports, loads the book data, computes aggregate statistics (count, price range, average price, breakdown by rating), and renders a PDF with `reportlab`.
- **`GET /reports/{id}`** reports status and, once complete, a `download_url` — only the *link* is returned, never the PDF bytes themselves, keeping the status response small regardless of report size.
- **`GET /reports/{id}/download`** streams the actual PDF file, returning `409` if requested before the report is ready.

## What the report contains

- Total book count
- Price range (min/max) and average price
- Breakdown by star rating

Note: category breakdown currently shows everything as `"uncategorized"`, since the raw scraper output doesn't include a category field — that data only exists in the separate `llm-endpoint` enrichment pipeline, which wasn't wired into this report. A natural next step would be joining the two datasets.

## Idempotency

Requesting a new report within 5 minutes of an existing pending/running/completed report returns that same report instead of generating a duplicate. A failed report does not block a fresh retry — verified: after a report failed, the very next request created a genuinely new report; two requests immediately after that returned the same report ID.

## Retries and alerts

- A failed render is retried up to 3 times, with exponential backoff (2s, 4s).
- After the 3rd failure, the report is marked `failed` and a structured alert is written to `logs/alerts.jsonl`.
- Verified by removing the source data file: the worker logged `RETRY 1/3`, `RETRY 2/3`, then a real alert entry with the report ID, error, and attempt count.

## What I'd fix with another day

Wire in the category data from the `llm-endpoint` enrichment pipeline so the report's category breakdown reflects real values instead of "uncategorized." Also add a scheduled/recurring generation option (e.g. daily), since right now reports are only generated on demand.