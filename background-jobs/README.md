# Background Jobs — Accept Fast, Work in Background

Moves a slow LLM call out of the request/response cycle. `POST /jobs` answers instantly with `202`, a separate worker process does the actual work, and `GET /jobs/{id}` reports status.

Reuses the same book-enrichment LLM call (title + description → category/summary/quality_flags) from the earlier LLM endpoint assignment, now running as a background job instead of inline.

## Try it

```bash
# Submit a job — returns instantly
curl -X POST http://localhost:8002/jobs \
  -H "Content-Type: application/json" \
  -d '{"title":"A Light in the Attic","description":"A collection of poetry."}'
```

Response (immediate):
```json
{"job_id":"...","status":"pending"}
```

```bash
# Check status
curl http://localhost:8002/jobs/<job_id>
```

Response (once the worker finishes):
```json
{
  "job_id": "...",
  "status": "completed",
  "result": {"category": "poetry", "summary": "...", "quality_flags": []},
  "error": null,
  "attempts": 1,
  "created_at": "...",
  "updated_at": "..."
}
```

## How to run

Requires [Ollama](https://ollama.com) installed and `gemma3:1b` pulled (`ollama pull gemma3:1b`).

```bash
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env   # fill in the values below

# Terminal 1 — the API
uvicorn src.main:app --reload --port 8002

# Terminal 2 — the worker (separate process, polls for jobs)
python src/worker.py
```

## Environment variables

LLM_BASE_URL=http://localhost:11434/v1/
LLM_API_KEY=ollama
LLM_MODEL=gemma3:1b

## The pattern

- **`POST /jobs`** validates input, stores a job row as `pending`, and returns `202` immediately — no model call happens on this request.
- **The worker** (`src/worker.py`) runs as a separate, always-on process. It polls the job table every 2 seconds, claims one pending job at a time, calls the model, and saves the result.
- **`GET /jobs/{id}`** reports the job's current status (`pending` / `running` / `completed` / `failed`), and the result once available.

## Idempotency

Submitting the exact same input twice does not create two jobs — the second request returns the existing job's ID and current status, as long as that job hasn't already failed. Verified: two identical `POST /jobs` calls returned the same `job_id`.

## Retries and alerts

- A failed model call is retried up to 3 times total, with exponential backoff (2s, 4s) between attempts.
- After the 3rd failure, the job is marked `failed` permanently and a structured alert is written to `logs/alerts.jsonl` (and printed to the worker's console) — this is the "someone must find out" mechanism.
- Verified by pointing at a nonexistent model name: the worker logged `RETRY 1/3`, `RETRY 2/3`, then wrote a real alert entry with the job ID, error, and attempt count.

## Known issue hit during development

Running multiple worker processes accidentally (from not fully closing old terminals) caused a stray old worker to silently complete a test job before a newly-restarted worker could pick it up, producing a confusing false result during retry testing. Killing all stray `python` processes before testing resolved it. This is itself a good illustration of why idempotent, atomic job-claiming (`claim_next_job`) matters — if two workers ever really did run concurrently in production, the `UPDATE ... WHERE status = 'pending'` guard prevents them from double-processing the same job.

## What I'd fix with another day

The worker currently polls on a fixed 2-second interval regardless of load. A real system would likely use a proper queue (e.g. Redis, SQS) instead of polling a SQLite table, and would run multiple worker instances safely in parallel — the current single-worker-at-a-time design is intentionally simple for this assignment.