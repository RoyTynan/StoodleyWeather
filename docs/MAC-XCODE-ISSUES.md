# Local Dev — Xcode / Android Constraints

## Why this setup exists

A project named v4visuals I'm working on (most of 2026) is a React Native mobile app built with Expo. Development requires Xcode to run the iOS and Android Studio for Android simulators, build the app and deploy to actual test devices. It also requires a locally running Cloudflare Workers tunnel (`wrangler dev`) for the API layer. These are Mac-only constraints — neither can run on the i7 Ubuntu server.

As a result, all development tooling that previously ran on i7 has been moved to the Mac Mini, with the i9 retained solely for LLM inference due to its GPU capacity.

---

## Hardware

- **Mac Mini M2** — 32GB unified memory. Runs VS Code, Xcode, Cloudflare tunnel, Expo, Ollama, ChromaDB, MCP proxy and server.
- **i9 Ubuntu (192.168.178.99)** — LLM inference only. Runs Qwen2.5-Coder-32B-Instruct Q8_0 via llama-server on port 8080.
- **i7 Ubuntu (192.168.178.35)** — Runs MCP tools, ChromaDB, and embedding server. Receives synced copies of the Mac repo and keeps the RAG index up to date via its file watcher.

---

## Architecture

```
VS Code / Cline (Mac)
        ↓
  proxy.py :8000          ← enriches prompts with RAG context
        ↓
  ChromaDB (local)        ← vector + BM25 index of v4visuals
  Ollama :11434           ← nomic-embed-text embeddings (Metal, unified memory)
        ↓
  i9 llama-server :8080   ← Qwen2.5-Coder-32B-Instruct Q8_0 (LLM inference)
```

---

## Project Repo Location — Dual Copy with File Sync

The React Native repo must live on the Mac — Xcode and the iOS/Android simulators require local access to the source. But the RAG indexing system (ChromaDB, the file watcher, the embedding server) runs on the i7 Ubuntu server, which is where the full AI setup lives.

To bridge this, the project runs as **two synchronised copies**:

```
Mac Mini                          i7 Ubuntu
~/dev/v4/v4visuals/    ←sync→    /home/roy/mcp-context/repos/v4visuals/
  (edit here, run Expo/Xcode)       (indexed here, RAG always up to date)
```

A local file watcher on the Mac monitors the repo for changes and syncs modified files to the i7 automatically. This means:

- You code and run the app entirely on the Mac
- The i7's file watcher detects the incoming changes, triggers a re-index, and keeps ChromaDB current
- Every Cline request is enriched with up-to-date RAG context from the i7, even though the code lives on the Mac

### Why not index on the Mac?

The Mac setup does have a local ChromaDB (used as a fallback), but the i7 is the preferred indexing target because:

- It runs the embedding server (`nomic-embed-text` via llama.cpp) at full speed on the RTX 2060
- It keeps the Mac free of indexing load during development
- The i7's MCP tools and proxy are already configured and battle-tested

### Mac-side proxy REPO_ROOT

The local `config.py` on the Mac still points `REPO_ROOT` at the Mac copy:

```
/Users/yourname/dev/v4
```

This is used by the Mac proxy for any local context injection fallback. The i7 proxy uses its own `REPO_ROOT` pointing at the synced copy on Ubuntu.

---

## Project Repo Location — Mac Only (original approach)

Before the dual-copy sync approach was adopted, the repo lived only on the Mac and was indexed locally. This section is retained as a reference for a simpler single-machine setup.

The proxy indexes whatever is under `REPO_ROOT`, which in `config.py` is set to:

```
/Users/yourname/dev/v4
```

Place the repo directly under that directory:

```
~/dev/v4/
└── v4visuals/        ← React Native project here
```

ChromaDB runs locally on the Mac (`~/dev/mcp-tools/chromadb_data/`) and is populated by running the indexer manually after significant changes:

```bash
cd ~/dev/mcp-tools && .venv/bin/python index_repos.py --repo v4visuals
```

If you use a different root path, update `REPO_ROOT` in `config.py` to match before running the indexer. This approach works well on a single machine but means the i7's RAG system has no knowledge of the Mac repo.

---

## MCP Tools

Location: `~/dev/mcp-tools/`

The Mac-specific versions of all Python scripts are in [_python-files-xcode/](../_python-files-xcode/) in this repo. Copy the contents of that folder to `~/dev/mcp-tools/` on the Mac and run `uv sync`.

| File | Purpose |
|---|---|
| [`config.py`](../_python-files-xcode/config.py) | All paths and endpoints. Edit here if anything moves. **See note below.** |
| [`proxy.py`](../_python-files-xcode/proxy.py) | FastAPI proxy on port 8000. Intercepts Cline's LLM requests, injects RAG context (hybrid BM25 + vector search via RRF), forwards to i9. |
| [`server.py`](../_python-files-xcode/server.py) | stdio MCP server. Provides `semantic_search`, `read_repo_file`, `list_repos`, `search_official_docs`, `verify_project` tools to Cline. |
| [`verify.py`](../_python-files-xcode/verify.py) | Stack auto-detection and check runner used by `verify_project`. |
| [`index_repos.py`](../_python-files-xcode/index_repos.py) | Indexes source repos into local ChromaDB. Run manually after large changes. |
| [`index_docs.py`](../_python-files-xcode/index_docs.py) | Indexes documentation libraries into ChromaDB. |
| [`docs_server.py`](../_python-files-xcode/docs_server.py) | stdio MCP server for documentation search. |

### config.py — DOCS_SOURCES

The `DOCS_SOURCES` constant in [`config.py`](../_python-files-xcode/config.py) is project-specific. The version in `_python-files-xcode/` is configured for this project (typescript, react-native, expo, skia). If you are setting this up for a different project you will need to update `DOCS_SOURCES` to match the documentation libraries you have downloaded and indexed.

See [ADDING-DOCS.md](ADDING-DOCS.md) for the full process of downloading, indexing, and registering each library.

---

### Start / stop the proxy
```bash
# Start
cd ~/dev/mcp-tools && .venv/bin/python proxy.py

# Stop
pkill -f proxy.py
```

The proxy is started manually — it does not run at login.

---

## Ollama (embeddings)

Ollama runs as a Homebrew service and starts at login:
```bash
brew services start ollama   # start
brew services stop ollama    # stop
```

Model: `nomic-embed-text` loaded from local GGUF:
```
~/dev/mcp-tools/models/nomic-embed-text-v1.5.Q4_K_M.gguf
```

Registered via Modelfile — no internet download required.

---

## ChromaDB

Location: `~/dev/mcp-tools/chromadb_data/`

Indexed repos: **v4visuals only** (stoodleyweather remains indexed on i7).

To re-index after significant code changes:
```bash
cd ~/dev/mcp-tools && .venv/bin/python index_repos.py --repo v4visuals
```

---

## Cline Configuration

**MCP server** (`~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`):
```json
"context-engine": {
  "command": "/Users/roytynan/dev/mcp-tools/.venv/bin/python",
  "args": ["/Users/roytynan/dev/mcp-tools/server.py"]
}
```

**LLM endpoint** (set in Cline UI):
- Provider: `OpenAI Compatible`
- Base URL: `http://localhost:8000/v1`
- Model: `Qwen2.5-Coder-32B-Instruct-Q8_0.gguf`
- API Key: `local`

---

## v4visuals Project

v4visuals is a commercial project. No source code is presented in this documentation.

Three layers:
- **React Native mobile app** — `ui/`
- **Express server** — `server/`
- **Cloudflare Workers API** — `server/api/cloudflare/`

Cline rules: `.clinerules/` at the project root covering coding style, behaviour, search format, API rules, environment variables, and approved packages — split per layer.

---

## Hybrid AI Workflow

- **Claude Code** — used for interactive, back-and-forth coding tasks. Has direct file access and full project context.
- **Cline + Qwen** — used for longer autonomous tasks. RAG context injection means Qwen has relevant code chunks for the specific task. Slower but can run unattended.
