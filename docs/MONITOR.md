# LLM Monitor

A local web dashboard that shows a full audit trail of every Cline task — what was injected, what was sent to the LLM, what it returned, and the token counts at each step.

```bash
cd frontend-llmmonitor
npm run dev
# opens at http://localhost:3333
```

---

## What It Shows

Every Cline task appears as a **task card** — a collapsible group of steps in the order they occurred.

### Task Card Header

| Field | Description |
|---|---|
| User task | The original typed prompt (extracted from `<task>` tags in Cline's message) |
| Repo badge | Repo detected from the conversation |
| Step count | Total steps in the task |
| Total latency | Sum of LLM latency across all steps in ms |
| Timestamp | When the task started |

### Step Timeline

Expand a task card to see each step as a row. Each step has:

- A **type badge** (coloured by step type — see below)
- A **preview** — filename for reads/writes, command text for shell commands, the user task for the opening step
- **Context badges** — `S` (skeleton injected), `C` (chunks injected), `V` (verify result injected)
- **Model badge** — which LLM served the response (e.g. `qwen2.5-coder-32b`)
- **Token counts** — `{prompt_tokens}↑ {completion_tokens}↓`
- **Latency** in ms

Click any step to expand it — showing the full enriched message sent to the LLM and the full response returned.

---

## Step Types

| Type | Colour | What it means |
|---|---|---|
| `TASK` | Gray | Opening prompt — the user's typed task |
| `READ` | Dark gray | Cline read a file via `read_repo_file` |
| `WRITE` | Purple | Cline wrote or edited a file. Triggers verify and dependency impact analysis |
| `CMD` | Yellow | Cline ran a shell command |
| `ERROR` | Red (dim) | LLM connection error or unexpected exception — full error message logged |
| `HALT` | Red (bright) | Context saturation — proxy terminated the task and blocked retries |
| `DONE` | Teal | Task completed successfully (`attempt_completion`) |
| `FOLLOWUP` | Orange | User follow-up within the same task |
| `TOOL` | Dark gray | MCP tool call (semantic search, verify, etc.) |
| `PROMPT` | Blue | Other prompt not matching a specific category |

The step type legend at the top of the page is interactive — click any badge to see a description of what that step type means. Click again to close, or click a different badge to switch.

### ERROR vs HALT

- `ERROR` — the LLM server was unreachable (`Connection refused`) or returned an unexpected exception. The next request is not blocked — retrying after the LLM is restarted will work.
- `HALT` — the LLM returned an empty response (context saturation). The next request for the same task is blocked. Start a new Cline task with a more focused prompt.

---

## HALT Steps

A `HALT` step (bright red) means the LLM returned an empty response — typically caused by context window saturation. When this happens the proxy:

1. Logs the step as `HALT`
2. Returns an `attempt_completion` response to Cline telling the user the query was too large
3. Blocks any retry for the same task — so Cline cannot spiral into repeated failed requests

If you see a HALT, start a new Cline task with a more focused prompt. Use the codebase skeleton and RAG context to your advantage rather than asking the model to read the entire project.

---

## Config Panel

The **Config** button at the top right opens a panel showing the proxy configuration that was active at the last startup:

| Setting | Description |
|---|---|
| `N_CONTEXT_CHUNKS` | Number of code chunks injected per prompt |
| `SKELETON_MAX_FILES` | Max files included in the skeleton map |
| `CHUNK_CHARS` | Characters per chunk |
| `CHUNK_OVERLAP` | Overlap between chunks |
| `LLM_URL` | LLM server address |
| `EMBED_URL` | Embedding server address |
| Startup time | When the proxy last started |

Config is snapshotted to SQLite at every proxy startup — so the panel always shows what was active when the logs were produced.

---

## Delete Controls

**Delete All** — button at the top right. Opens a modal showing the number of tasks that will be deleted. Requires confirmation before proceeding. Clears the entire `prompt_log` database.

**Delete task** — each task card has a two-stage delete button. First click shows a confirmation state; second click deletes the task and all its steps.

---

## Architecture

The monitor is a Next.js app in `frontend-llmmonitor/`. It reads directly from the SQLite database at `/mnt/storage/prompt_log.db` using `better-sqlite3`.

- Main page: `app/page.tsx`
- Database queries: `lib/db.ts`
- Task list API: `app/api/tasks/route.ts`
- Per-task delete: `app/api/tasks/[taskId]/route.ts`
- Step detail: `app/api/prompts/[id]/route.ts`
- Config: `app/api/config/route.ts`

The monitor runs on port 3333 to avoid conflicting with the Next.js dev server for the weather app (port 3000).

---

## Reading the Logs

**Understanding a task:** Expand the task card and look at the step sequence. A typical healthy task:

```
TASK   → user's opening prompt
READ   → Cline reads a file
WRITE  → Cline writes an edit
TOOL   → verify_project runs
DONE   → attempt_completion
```

**Checking what was injected:** The `S`, `C`, `V` badges on each step show whether skeleton, code chunks, and verify results were injected. If neither `S` nor `C` is present, enrichment was skipped — either because Cline sent an internal tool result, or because the prompt contained a direct file path.

**Checking token pressure:** High `prompt_tokens` values on a step (above ~40,000) mean the context window is approaching its limit. A HALT step at the end of a high-token sequence is expected — it means the proxy caught saturation before Cline could retry indefinitely.

**Comparing models:** The model badge shows which LLM served each step. In a multi-machine setup with separate embedding and inference servers, this confirms which machine handled the request.
