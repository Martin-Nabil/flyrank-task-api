# AI Decision Flow — React Flow + Inngest

A visual workflow builder where each node is an AI decision step that answers exactly YES or NO, executed through Inngest and visualized with React Flow.

## What it does

- Build a graph of decision nodes on a visual canvas (drag, connect, edit prompts)
- Connect nodes with YES or NO labeled edges
- Click "Run Workflow" — the graph executes for real: each node's prompt is sent to a local LLM (via Ollama), the model answers YES or NO, and execution follows the matching edge to the next node
- Results appear both in an execution log panel and directly on each node (with a highlighted "active" state)

## Stack

- Next.js (App Router, JavaScript)
- React Flow — the visual canvas
- Inngest — workflow execution engine (each node = one Inngest step)
- OpenAI SDK, pointed at Ollama (free, local, no API key/billing risk)
- Shadcn — component library (installed, available for future UI work)

## How to run

Requires [Ollama](https://ollama.com) installed with `gemma3:1b` pulled:
```bash
ollama pull gemma3:1b
```

```bash
npm install
cp .env.example .env.local   # fill in the values below
```

`.env.local`:
LLM_BASE_URL=http://localhost:11434/v1/
LLM_API_KEY=ollama
LLM_MODEL=gemma3:1b
INNGEST_DEV=1

Then run **two** processes in separate terminals:

```bash
# Terminal 1 — the Next.js app
npm run dev

# Terminal 2 — the Inngest dev server (discovers and runs your functions)
npx inngest-cli@latest dev
```

Open `http://localhost:3000` for the app, `http://localhost:8288` for the Inngest dashboard (useful for inspecting individual runs/steps).

## How execution works

1. The canvas graph (`nodes`, `edges`) lives in React state on the frontend.
2. Clicking "Run Workflow" sends the graph to `/api/run-workflow`, which fires an Inngest event (`workflow/run`).
3. The Inngest function (`src/inngest/functions.js`) walks the graph starting from the first node: for each node, `step.run(...)` calls the LLM with that node's prompt, gets back exactly YES or NO, and picks the outgoing edge whose branch matches — repeating until there's no next node.
4. The full execution log (every node visited, its prompt, its answer) is written to a local file (`run-results/{eventId}.json`) as well as returned as the function's result.
5. The frontend polls `/api/run-status/{eventId}` every 1.5s until the result file appears, then displays it — both in a log panel and directly on each executed node.

## Known limitation

Inngest's local dev server REST API (`/v1/events/{id}/runs`) did not reliably return the function's actual output during development/testing — it consistently returned an empty string even for genuinely completed runs, even though the Inngest dashboard UI showed the correct output. Rather than depend on that endpoint, the app writes its own result file locally and polls that instead — more reliable, and not dependent on an internal/dev-only API behavior that may differ from Inngest's production API.

## Model accuracy note

Using `gemma3:1b` (a very small, free, local model) for the AI decision nodes means answers aren't always factually correct — during testing, it answered "NO" to "Is the sky blue?" This is expected behavior for a lightweight model and not a bug in the pipeline; the system correctly passes through whatever the model decides without attempting to silently correct it.

## What's built (per the brief)

**Phase 1 — Setup:** Next.js app, React Flow / Inngest / OpenAI SDK / Shadcn installed, env configured.

**Phase 2 — Foundations:** interactive canvas, add/connect/edit nodes, YES/NO edge types, graph state stored locally (React state).

**Phase 3 — Build (core):** each node maps to a real Inngest step, sends its prompt to the LLM, model returns exactly YES/NO, execution follows the matching edge, full execution order tracked and returned.

**Phase 4 — Polish (3 of the list):**
- Execution logs panel — real per-node results shown in the UI
- Visual execution state — executed nodes highlighted with an amber glow and their answer displayed directly on the node
- Better node styling — custom-styled decision nodes instead of React Flow's default plain boxes