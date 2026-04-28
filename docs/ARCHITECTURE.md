# Architecture

How the system is structured and how the pieces interact.

---

## System Overview

```
VS Code / Cline
      |
      | POST /v1/chat/completions
      v
proxy.py  (i7, port 8000)
      |
      |-- detect repo from conversation
      |-- hybrid search (vector + BM25 + rerank)
      |-- inject skeleton + chunks into prompt
      |-- log request to prompt_log.db
      |
      | POST /v1/chat/completions (enriched)
      v
llama-server  (i9, port 8080)
      |
      | streaming response
      v
proxy.py  (captures response text, latency, token counts)
      |
      v
VS Code / Cline
```

Alongside this, Cline connects directly to two MCP servers on the i7:
- **context-engine** (`server.py`) — repo file access, semantic search, verify
- **docs-engine** (`docs_server.py`) — framework documentation search

---

## Proxy — Context Enrichment

`proxy.py` is a FastAPI server on the i7 (port 8000). Every request Cline sends is intercepted before it reaches the LLM.

**What it does per request:**

1. Scans the conversation history to detect which repo is being worked on
2. Runs a hybrid search to find the most relevant code chunks from ChromaDB
3. Injects a codebase skeleton map, code chunks, and any pending verify/impact results into the prompt
4. Forwards the enriched prompt to the i9 LLM
5. Captures the response, strips thinking blocks if `LLM_HAS_THINKING` is set, logs everything to SQLite

**Enrichment is skipped when:**
- The message starts with `[` — it's a Cline internal tool result, not a user prompt
- The message contains a file path matching `src/...` — Cline reads the file directly via the MCP server instead, giving the model clean accurate content for edits

### Hybrid Search

Two retrieval methods run in parallel and are merged using **Reciprocal Rank Fusion (RRF)**:

- **Vector search** — embeds the prompt using bge-m3 and queries ChromaDB for semantically similar chunks
- **BM25 keyword search** — scores all chunks in an in-memory BM25 index (built at proxy startup) using TF-IDF-style keyword matching

RRF combines the two ranked lists into a single ranking without normalising scores — chunks that rank well in both searches score highest. The top candidates are passed to the **cross-encoder reranker** (ms-marco-MiniLM-L-6-v2) which scores each chunk against the query as a pair, giving a more precise final selection than vector similarity alone.

The top `N_CONTEXT_CHUNKS` results are injected into the prompt.

### Skeleton Injection

At startup the proxy builds a compact **skeleton map** for each repo — one line per file listing its exported symbols:

```
src/components/WeatherChart.tsx → WeatherChart, WeatherChartProps
src/lib/weather-utils.ts → formatTemperature, windChill, celsiusToFahrenheit
```

This gives the LLM the full codebase structure upfront cheaply, without reading every file. It is injected before the code chunks on every enriched request.

### HALT Detection

When the LLM returns an empty response — typically caused by context window saturation — the proxy:

1. Logs the step as `HALT` in the prompt database
2. Returns a valid Cline `attempt_completion` response telling the user the query was too large and to start a new task with a more focused prompt
3. Blocks the next retry for the same task — so Cline cannot spiral into repeated failed requests

This stops the retry death spiral: each retry would resend the full conversation history, making context saturation worse with every attempt.

### LLM-Down Detection

Connection errors to the LLM server (`httpx.ConnectError`) are handled separately from context saturation:

- Logged as `ERROR` step type (not `HALT`)
- Cline receives an `attempt_completion` message: *"The LLM server is not reachable — start the LLM on the i9 and retry"*
- The next request is **not** blocked — when the LLM comes back up, Cline can retry normally

Any other unexpected exception is also logged as `ERROR` with the full exception type and message persisted to the database.

### Thinking Mode

Some models (Qwen3, DeepSeek-R1) output `<think>...</think>` blocks before tool calls. Cline's XML tool call parser cannot handle these — it sees `<think>` as an unknown tool and fails.

When `LLM_HAS_THINKING = True` in `config.py`, the proxy:

1. Adds `"enable_thinking": false` to every request body sent to the LLM — disabling think blocks at the model level
2. Strips any `<think>...</think>` blocks from the response as a safety net before passing content to Cline
3. After stripping, re-checks whether the response is empty — so HALT still fires correctly if think blocks were the only content

Set `LLM_HAS_THINKING = False` when using models that do not have a thinking mode (Qwen2.5, Llama, etc.).

### File Watcher

The proxy runs a **watchdog** file watcher over all repos under `REPO_ROOT`. When a file is saved, it triggers a re-index of that repo after a 3-second debounce. ChromaDB is always up to date with current file contents.

After a file write is detected (via Cline's `write_to_file` / `replace_in_file` tool result), the proxy also schedules a **verify run** — running type-check and lint on the repo and injecting the result into the next prompt so the LLM knows whether its edit passed or failed.

**inotify limit:** The file watcher requires a higher inotify watch limit than the Ubuntu default. See [SETUP.md](SETUP.md) for the sysctl command.

### Dependency Graph

At index time, `index_repos.py` parses `import` and `require` statements from all `.ts`, `.tsx`, `.js`, `.jsx`, and `.py` files and writes import edges to a SQLite database (`dep_graph.db`):

```
repo          file                              imports_file
stoodleyweather  src/components/WeatherTable.tsx  src/lib/weather-utils.ts
stoodleyweather  src/components/SummitConditions.tsx  src/lib/weather-utils.ts
```

When the proxy detects a file write, it queries `dep_graph.db` for files that import the edited file. If any are found, an **impact note** is injected into the next prompt:

```
Dependency impact: `src/lib/weather-utils.ts` is also imported by:
  - src/components/WeatherTable.tsx
  - src/components/SummitConditions.tsx
```

This tells the LLM which other files may be affected by its edit — so it can check for type errors or broken calls without being explicitly asked.

`MAX_IMPACT_FILES` caps the list. `DEP_GRAPH_ENABLED = False` disables the feature entirely.

---

## SQLite Databases

Two SQLite databases are used by the system.

### prompt_log.db

Every request and response is logged to `/mnt/storage/prompt_log.db`. The `prompts` table schema:

| Column | Description |
|---|---|
| `id` | Auto-increment primary key |
| `timestamp` | UTC timestamp |
| `repo` | Detected repo name |
| `raw_query` | Original user message before enrichment |
| `enriched_message` | Message after skeleton/chunk injection |
| `full_messages` | Full message array sent to LLM (JSON) |
| `skeleton_injected` | 1 if skeleton was injected |
| `chunks_injected` | 1 if code chunks were injected |
| `verify_injected` | 1 if a verify result was injected |
| `finish_reason` | LLM finish reason |
| `response_text` | LLM response text (think blocks stripped) |
| `latency_ms` | End-to-end latency |
| `model` | Model name returned by the LLM server |
| `task_id` | UUID grouping all steps of one Cline task |
| `step_type` | TASK / READ / WRITE / CMD / ERROR / HALT / DONE / FOLLOWUP / TOOL / PROMPT |
| `user_task` | Clean typed prompt (extracted from `<task>` tags) |
| `prompt_tokens` | Input token count |
| `completion_tokens` | Output token count |

The schema self-migrates on proxy startup — missing columns are added via `ALTER TABLE` so the database survives proxy upgrades without manual intervention.

A `config_snapshots` table records all proxy config values on every startup, timestamped, so you can see what settings were active for any given session. This includes all tuning constants (`N_CONTEXT_CHUNKS`, `LLM_HAS_THINKING`, `DEP_GRAPH_ENABLED`, etc.).

### dep_graph.db

The dependency graph lives at `/mnt/storage/chromadb/dep_graph.db`. Built by `index_repos.py` on every index run.

**`edges` table:**

| Column | Description |
|---|---|
| `repo` | Repo name |
| `file` | The file that contains the import |
| `imports_file` | The file being imported (repo-relative path) |

The primary key is `(repo, file, imports_file)`. All edges for a repo are deleted and rebuilt on each full index run — the table always reflects the current state of the codebase.

Relative imports are resolved to canonical repo-relative paths at index time, with extension probing (`.ts`, `.tsx`, `.js`, `.jsx`, `.py`) and index file detection (`index.ts` etc.). External package imports are ignored.

---

## ChromaDB

An open-source Python-native vector database. Stores embeddings of all source files and documentation.

- **Location:** `/mnt/storage/chromadb/` on the i7
- **Collections:** one per repo (`repo_<name>`) and one per documentation library (`docs_<name>`)
- **Persistence:** writes to disk immediately — no load-on-boot step needed
- **Chunk size:** 600 characters with 120-character overlap (source); 800/120 (docs)

Each chunk is stored with metadata: `file_path`, `start_line`, `end_line`, `repo`.

### .chromaignore

Each repo can have a `.chromaignore` file in its root to exclude files from indexing. One pattern per line, `#` for comments. Supports glob patterns via `fnmatch` — `**` works as a wildcard, trailing slashes are stripped. Negation (`!`) is not supported.

```
# Example .chromaignore
spikes/
visual-test-data/
*/public/weather-data/
```

---

## Embeddings — bge-m3

`bge-m3-Q8_0` runs as a systemd service (`llama-embed`) on the i7's RTX 2060 (port 11435). It produces 1024-dimensional embeddings.

bge-m3 requires prefixes:
- `query: ` — prepended to prompts before embedding at query time
- `passage: ` — prepended to document chunks before embedding at index time

Used by `index_repos.py`, `index_docs.py`, and `proxy.py`.

---

## MCP Servers

Two FastMCP servers run on the i7. Cline launches them automatically via SSH when VS Code starts.

### context-engine (server.py)

| Tool | What it does |
|---|---|
| `list_repos` | Lists all repos under `REPO_ROOT` |
| `read_repo_file` | Reads a specific file from a repo |
| `semantic_search` | Queries ChromaDB for relevant chunks |
| `search_official_docs` | Ripgrep keyword search over documentation |
| `read_doc_page` | Reads a specific documentation file |
| `verify_project` | Runs type-check and lint on a repo |

### docs-engine (docs_server.py)

| Tool | What it does |
|---|---|
| `search_nextjs_docs` | Semantic search over Next.js documentation |
| `search_react_docs` | Semantic search over React documentation |
| `search_typescript_docs` | Semantic search over TypeScript documentation |

Two servers rather than one keeps the tool list per server short, which reduces the system prompt length and makes it easier for the model to generate correctly formatted tool calls.

---

## Verify

`verify.py` auto-detects the project stack and runs the appropriate checks:

| What it finds | What it runs |
|---|---|
| `tsconfig.json` or `typescript` in `package.json` | `tsc --noEmit` |
| `react` in `package.json` | `tsc --noEmit` + ESLint |
| `CMakeLists.txt` | `cmake --build build/` |
| `Makefile` | `make -j4` |

Verify runs automatically after every file write detected by the proxy. The result is injected into the next prompt so the LLM knows whether its edit compiled cleanly.

---

## Python Scripts Reference

All scripts live in `/mnt/storage/mcp-tools/`. Copies are in [`_python-files/`](../_python-files/).

| File | Purpose |
|---|---|
| `config.py` | All configuration — edit this to match your machine |
| `proxy.py` | LLM proxy — enrichment, file watcher, logging, HALT detection |
| `server.py` | context-engine MCP server |
| `docs_server.py` | docs-engine MCP server |
| `verify.py` | Stack detection and check runner |
| `index_repos.py` | Repo indexer — builds ChromaDB collections |
| `index_docs.py` | Documentation indexer |
| `rerank.py` | Cross-encoder reranker |
| `watcher.py` | Standalone file watcher — monitors repos and triggers re-indexing on change |
| `context_bridge_server.py` | MCP server providing a key-value context store (SQLite-backed) |
| `start-proxy.sh` | Shortcut to start `proxy.py` |
| `start-services.sh` | Post-reboot health check |
| `update-docs.sh` | Pull and re-index all documentation sources |
