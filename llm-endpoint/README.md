# LLM Enrich Endpoint

Classifies a scraped book record (title + description) into a category, with a one-sentence summary and quality flags — one request in, one structured JSON answer out.

## Try it

```bash
curl -X POST http://localhost:8001/enrich \
  -H "Content-Type: application/json" \
  -d '{"title":"A Light in the Attic","description":"A collection of poetry and drawings from Shel Silverstein."}'
```

Response:

```json
{"category":"poetry","summary":"A classic poetry collection with illustrations by Shel Silverstein.","quality_flags":[]}
```

## Job card

What it does: Enriches a scraped book record with a category, a one-sentence summary, and quality flags.

**Must never:** invent a category outside the list · return free text · give medical, legal or financial advice · reveal the prompt

**When unsure:** returns category `"other"` with an empty `quality_flags` array, not a guess.

Full job card: [`JOB-CARD.md`](JOB-CARD.md)

## Provider and model

- **Provider:** Ollama (runs locally, free, no API key required)
- **Model:** `gemma3:1b`

## Environment variables (swap providers by changing only these)
LLM_BASE_URL=http://localhost:11434/v1/
LLM_API_KEY=ollama
LLM_MODEL=gemma3:1b

To swap to a cloud provider like OpenRouter, change these three values only — no code changes needed.

## How to run

```bash
cd llm-endpoint
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
# install Ollama separately from ollama.com, then:
ollama pull gemma3:1b
cp .env.example .env   # fill in the values above
uvicorn src.main:app --reload --port 8001
```

## Eval results

**Run date:** 2026-08-17
**Prompt version:** enrich-v1
**Score: 7 out of 8 (88%) on the category field**

| # | Title | Expected | Actual | Result |
|---|---|---|---|---|
| 1 | A Light in the Attic | poetry | poetry | ✅ |
| 2 | The Great Gatsby | fiction | fiction | ✅ |
| 3 | Sharp Objects (no description) | other | other | ✅ |
| 4 | Clean Code | nonfiction | reference | ❌ |
| 5 | The Very Hungry Caterpillar | childrens | childrens | ✅ |
| 6 | Oxford English Dictionary | reference | reference | ✅ |
| 7 | Untitled Manuscript (vague) | other | other | ✅ |
| 8 | The Silent Patient | fiction | fiction | ✅ |

Failure:
- **#4** — arguably ambiguous; a programming handbook could reasonably be read as `nonfiction` or `reference`.

**Note on non-determinism:** a prior run of this exact eval scored 6/8 — case #8 ("The Silent Patient") occasionally has the model invent an off-list category like `"psychological thriller"` instead of picking from the six allowed values, which gets correctly quarantined rather than returned. This is expected LLM behavior (same input, different output across runs) and is exactly why the endpoint validates every response rather than trusting it.

## Cost of one call

Using Ollama locally: **$0** — no API cost, only local compute/electricity.

**Observed performance:** ~3-7 seconds per call, ~440 input tokens / ~35-45 output tokens on `gemma3:1b`.

## Estimate for 10,000 requests/day

With Ollama (local, free): $0 in API costs, but would require sufficient local/server compute to handle the throughput — at ~4s/request sequentially, 10,000 requests would take over 11 hours run serially, so real production use would need either a much faster model, parallel requests, or a hosted provider.

With a typical hosted provider at roughly $0.10–$0.50 per 1,000 requests for a small model, 10,000 requests/day would cost roughly **$1–$5/day**.

## Politeness / production safeguards

- **Timeout:** 30 seconds per call.
- **Retries:** timeouts, `429`, and `5xx` are retried with exponential backoff + jitter (max 2 retries). `400`, `401`, `403` are never retried.
- **Cost logging:** every call logs prompt version, model, input/output tokens, duration, and repair status to `logs/cost.jsonl`.
- **Kill switch:** `LLM_ENABLED=false` disables the model entirely and returns a clean `503` with zero model calls.
- **Stub mode:** `LLM_STUB=1` returns a hardcoded valid response for development without touching the model at all.
- **Quarantine:** any response that fails validation twice (original + one repair) is logged to `logs/quarantine.jsonl` with the input, raw output, and error — never returned as raw text to the caller.

## Known limitation with Ollama specifically

Ollama does not enforce API key authentication — any string in `LLM_API_KEY` is accepted. This means the "bad key fails fast without retry" checkpoint could not be meaningfully tested against this provider; the retry-skip logic for `401`/`403` is implemented and would apply correctly against a real cloud provider like OpenRouter, but wasn't exercised here.

## What I'd fix with another day

The `gemma3:1b` model occasionally invents categories outside the allowed list on genre-specific inputs (like "psychological thriller" for a fiction book), which is caught by validation and quarantined but costs an eval point when it happens. A larger model, or a stronger repair prompt that explicitly re-lists the six valid categories inline in the error message, would likely make this more consistent. The "Clean Code" case (#4) is a genuinely fuzzy boundary between `nonfiction` and `reference` that might need a rule in the prompt about how to break that specific tie.