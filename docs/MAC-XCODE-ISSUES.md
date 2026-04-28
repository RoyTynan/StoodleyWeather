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
  Ollama :11434           ← bge-m3 embeddings (Metal, unified memory)
        ↓
  i9 llama-server :8080   ← Qwen2.5-Coder-32B-Instruct Q8_0 (LLM inference)
```

---

## Project Repo Location — Dual Copy with Automated File Sync

The React Native repo must live on the Mac — Xcode and the iOS/Android simulators require local access to the source. But the RAG indexing system (ChromaDB, the embedding server) runs on the i7 Ubuntu server.

To bridge this, the project runs as **two synchronised copies**:

```
Mac Mini                          i7 Ubuntu
~/dev/v4/v4visuals/    ──────→   /home/roy/mcp-context/repos/v4visuals/
  (edit here, run Expo/Xcode)       (indexed here, RAG always up to date)
```

A local file watcher script runs on the Mac and monitors the repo for changes. When a file is saved, it rsyncs the changed file to the i7 over SSH. The i7's `mcp-indexer.service` (see [AUTO-INDEXING.md](AUTO-INDEXING.md)) detects the incoming changes, debounces, and triggers a reindex automatically. No manual steps required.

This means:
- You code and run the app entirely on the Mac
- The i7 stays in sync and keeps ChromaDB current automatically
- Every Cline request is enriched with up-to-date RAG context from the i7

### Why not index on the Mac?

- The i7 runs the embedding server (`bge-m3` via llama.cpp) at full speed on the RTX 2060 — faster than Mac Metal for this workload
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

All Python scripts are in [_python-files/](../_python-files/) in this repo. Copy the contents of that folder to `~/dev/mcp-tools/` on the Mac and run `uv sync`.

After copying, edit `config.py` for the Mac environment — see the section below.

### config.py — Mac values

| Setting | Mac value |
|---|---|
| `REPO_ROOT` | `/Users/yourname/dev/v4` |
| `CHROMA_DIR` | `/Users/yourname/dev/mcp-tools/chromadb_data` |
| `DOCS_ROOT` | `/Users/yourname/dev/mcp-tools/docs` |
| `TOOLS_DIR` | `/Users/yourname/dev/mcp-tools` |
| `EMBED_URL` | `http://127.0.0.1:11434/api/embeddings` (Ollama, not llama-embed) |
| `INDEXABLE_EXTENSIONS` | Remove `.py`, `.cpp`, `.h`, `.c` if not needed |
| `EXCLUDED_DIRS` | Add `"ios"`, `"android"`, `"Pods"`, `".expo"` |

Remove the `EMBED_QUERY_PREFIX` and `EMBED_PASSAGE_PREFIX` lines — Ollama does not use bge-m3 prefixes.

### config.py — DOCS_SOURCES

Update `DOCS_SOURCES` to match the documentation libraries you have downloaded for this project. The i7 version is configured for `nextjs` and `react`. The v4visuals Mac version uses `typescript`, `react-native`, `expo`, `skia`, `webgl`, `glsl`, and `webgl2-types`.

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

Model: `bge-m3` loaded from local GGUF:
```
~/dev/mcp-tools/models/bge-m3-Q8_0.gguf
```

Registered via Modelfile — no internet download required.

---

## ChromaDB

The primary ChromaDB index lives on the i7 and is kept up to date automatically by `mcp-indexer.service` as the Mac watcher syncs file changes over. Manual reindexing on the Mac is no longer required for normal development.

If needed, a full reindex can be forced on the i7:
```bash
ssh roy@192.168.178.35 "cd /mnt/storage/mcp-tools && .venv/bin/python index_repos.py --repo v4visuals --full"
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
