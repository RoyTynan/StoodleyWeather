# Local Dev — Xcode / Android Constraints

## Why this setup exists

A project named v4visuals I'm working on (most of 2026) is a React Native mobile app built with Expo. Development requires Xcode to run the iOS and Android Studio for Android simulators, build the app and deploy to actual test devices. It also requires a locally running Cloudflare Workers tunnel (`wrangler dev`) for the API layer. These are Mac-only constraints — neither can run on the i7 Ubuntu server.

As a result, all development tooling that previously ran on i7 has been moved to the Mac Mini, with the i9 retained solely for LLM inference due to its GPU capacity.

---

## Hardware

- **Mac Mini M2** — 32GB unified memory. Runs VS Code, Xcode, Cloudflare tunnel, Expo, Ollama, ChromaDB, MCP proxy and server.
- **i9 Ubuntu (192.168.178.99)** — LLM inference only. Runs Qwen2.5-Coder-32B-Instruct Q8_0 via llama-server on port 8080.
- **i7 Ubuntu (192.168.178.35)** — Unchanged. Runs stoodleyweather dev server, its own MCP tools, ChromaDB, and embedding server. No longer in the loop for Mac development.

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

## MCP Tools

Location: `~/dev/mcp-tools/`

The Mac-specific versions of all Python scripts are in [_python-files-xcode/](../_python-files-xcode/) in this repo. Copy the contents of that folder to `~/dev/mcp-tools/` on the Mac and run `uv sync`.

| File | Purpose |
|---|---|
| [`config.py`](../_python-files-xcode/config.py) | All paths and endpoints. Edit here if anything moves. **See note below.** |
| [`proxy.py`](../_python-files-xcode/proxy.py) | FastAPI proxy on port 8000. Intercepts Cline's LLM requests, injects RAG context (hybrid BM25 + vector search via RRF), forwards to i9. |
| [`server.py`](../_python-files-xcode/server.py) | stdio MCP server. Provides `semantic_search`, `read_repo_file`, `list_repos`, `search_official_docs` tools to Cline. |
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
