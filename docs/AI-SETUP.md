# Home AI Development Setup

## Introduction

A three-machine home LAN setup for AI-assisted software development. The Mac mini acts as a
thin client, the i7 handles development and tooling, and the i9 runs the large language model.

```
Mac mini (thin client)
    |
    | VS Code Remote SSH
    v
i7 Ubuntu  <----  VS Code + Cline extension
    |                MCP context-engine server
    |                RTX 2060 (embeddings only — NOT the LLM)
    |                /mnt/storage/ (repos, models, tools)
    |                proxy.py (port 8000) — enriches prompts with ChromaDB context
    |
    | HTTP (proxy → LLM API)
    v
i9 Ubuntu
    LLM — Qwen2.5-Coder-32B-Instruct-Q8_0.gguf
    RTX 3090 (24GB) + Blackwell RTX PRO 4000 (24GB) = 48GB VRAM
    (all AI reasoning and code generation)
```

> **Path and IP conventions:** Throughout this document, `/mnt/storage/` is the storage mount point on the i7 machine — replace it with your own path. IP addresses (`192.168.178.x`) are specific to this home network — replace them with the addresses of your own machines.

---

## 1. Machines

### Mac mini
- Thin client only
- **IP:** `<mac-mini-ip>` (e.g. 192.168.x.x)
- Runs VS Code, connects to i7 via Remote SSH

### i7 — Ubuntu
- Primary development machine
- **IP:** `<dev-machine-ip>`
- **CPU:** Intel Core i7
- **RAM:** 32GB
- **GPU:** NVIDIA RTX 2060, 6GB VRAM — used for embeddings only, does not run the LLM
- Hosts all repos, models, and MCP tooling under `/mnt/storage/`
- Runs the `llama-embed` systemd service and the MCP `context-engine` server

### i9 — Ubuntu
- Dedicated LLM inference machine
- **IP:** `<llm-machine-ip>`
- **CPU:** Intel Core i9
- **RAM:** 32GB
- **GPU 0:** NVIDIA RTX 3090 — 24GB VRAM
- **GPU 1:** NVIDIA Blackwell RTX PRO 4000 — 24GB VRAM
- **Total VRAM:** 48GB (llama.cpp splits model layers across both GPUs)
- Runs `Qwen2.5-Coder-32B-Instruct-Q8_0.gguf` (34.8GB) fully in GPU VRAM
- Exposes an OpenAI-compatible API at `http://<llm-machine-ip>:8080/v1`
- Used by Cline for all AI reasoning and code generation

---

## 2. How It Works

### Workflow

- **Cline + local LLM** — executing specific, well-defined coding tasks (add a function, edit a component, etc.)

 Cline  executes prompts against the local LLM.

### VS Code + Cline
VS Code runs on the Mac mini and connects to the project repo on the i7 via Remote SSH. The Cline extension sends all AI completions through the **proxy** running on the i7 at port 8000 — not directly to the i9. The proxy enriches every request with relevant code from ChromaDB before forwarding it to the LLM. Cline also connects to the `context-engine` MCP server on the i7 for direct file reads.

> **Note:** This setup was built and tested with **Cline v3.75**. It has not been tested against the latest version of Cline — configuration options and MCP settings may differ in newer releases.

### Cline Settings
In addition to the provider settings below, these Cline feature flags should be turned **off**:

| Setting | Value |
|---|---|
| Native Tool Call | Off |
| Parallel Tool Calling | Off |
| Focus Chain | Off |

These settings reduce prompt complexity and improve reliability with the local LLM.

### Proxy — Automatic Context Enrichment
`proxy.py` is a FastAPI server on the i7 (port 8000) that sits between Cline and the i9 LLM.

Every request Cline sends is intercepted. The proxy:

1. Scans the conversation history to detect which repo is being worked on
2. Embeds the user's prompt into a vector using the RTX 2060
3. Queries ChromaDB for the 5 most relevant code chunks from that repo
4. Injects them into the prompt before forwarding to the i9

**Exception:** if the prompt already contains a file path (`src/`), enrichment is skipped — Cline reads the file directly via the MCP server instead. This avoids format mismatches that would cause Cline's SEARCH/REPLACE edits to fail.

The proxy also runs a **file watcher** (watchdog) over all repos under `REPO_ROOT`. When a file is saved, it triggers a re-index of that repo after a 3-second debounce. This means ChromaDB is always up to date with the current file contents, not just what was last committed.

**Multi-repo support:** the proxy watches all repos under `REPO_ROOT` and detects the active repo from the conversation context automatically. No configuration change is needed when starting a new project.

### Semantic Search / RAG
Context enrichment now happens automatically via the proxy on every Cline request. The `semantic_search` MCP tool is still available but rarely needed — the proxy handles enrichment transparently.


### ChromaDB — Vector Database
All semantic search is backed by **ChromaDB**, an open-source, Python-native vector database.

**Why ChromaDB:**
- Pure Python — installs with `uv add chromadb`, no separate server process required
- Persists automatically to disk; data survives reboots without any manual intervention
- Supports metadata filtering (by file path, repo, library) so searches stay scoped
- Simple API that integrates directly into `server.py` without extra infrastructure
- Scales comfortably to hundreds of thousands of vectors on a single machine

**What it stores:**
Each source (project repo or documentation library) gets its own named *collection* — a set of
vector embeddings, where each embedding represents a chunk of code or documentation text.

**Where it lives:** `/mnt/storage/chromadb/` on the i7 machine

**Persistence:** ChromaDB writes to disk immediately. There is no load-on-boot step — the data
is always there after the first index run.

---

## 3. Downloads Required

### i9 — LLM Model

Download from HuggingFace using wget with a Bearer token:

```bash
wget --header="Authorization: Bearer your-huggingface-token" \
    https://huggingface.co/bartowski/Qwen2.5-Coder-32B-Instruct-GGUF/resolve/main/Qwen2.5-Coder-32B-Instruct-Q8_0.gguf \
    -O /home/yourusername/models/Qwen2.5-Coder-32B-Instruct-Q8_0.gguf \
    --continue --progress=dot:giga
```

`--continue` allows resuming an interrupted download. `--progress=dot:giga` shows progress in
GB increments — useful for a 34.8GB file.

### i7 — Embedding Model

```bash
python3 -c "
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id='nomic-ai/nomic-embed-text-v1.5-GGUF',
    filename='nomic-embed-text-v1.5.Q4_K_M.gguf',
    local_dir='/mnt/storage/models/'
)"
```

### i7 — Documentation Sources

```bash
# React docs
git clone https://github.com/reactjs/react.dev.git /mnt/storage/docs/frameworks/react-docs

# TypeScript docs (sparse clone — handbook and tsconfig reference only)
git clone --depth=1 --filter=blob:none --sparse https://github.com/microsoft/TypeScript-Website.git /mnt/storage/docs/frameworks/typescript-docs
git -C /mnt/storage/docs/frameworks/typescript-docs sparse-checkout set packages/documentation/copy/en packages/tsconfig-reference

# Next.js docs (sparse clone — docs/ only)
git clone --depth=1 --filter=blob:none --sparse https://github.com/vercel/next.js.git /mnt/storage/docs/frameworks/nextjs-docs
git -C /mnt/storage/docs/frameworks/nextjs-docs sparse-checkout set docs
```

See [ADDING-DOCS.md](ADDING-DOCS.md) for the full process of indexing each library into ChromaDB and wiring it into the MCP server.

---

## 4. Setting Up the i9

### Prerequisites
- Ubuntu installed, 24.04
- NVIDIA drivers installed and `nvidia-smi` working for both GPUs.  CUDA drivers installed (nvidia-smi working)
- `git` installed

### Build llama.cpp

```bash
git clone https://github.com/ggerganov/llama.cpp.git /home/yourusername/llama.cpp
cd /home/yourusername/llama.cpp
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release -j$(nproc)
```

### Create the startup script

Create `/home/yourusername/start-llm.sh`:

```bash
#!/bin/bash
pkill llama-server
sleep 2

SERVER_BIN="/home/yourusername/llama.cpp/build/bin/llama-server"
MODEL_PATH="/home/yourusername/models/Qwen2.5-Coder-32B-Instruct-Q8_0.gguf"

$SERVER_BIN \
  -m "$MODEL_PATH" \
  --host 0.0.0.0 \
  --port 8080 \
  -ngl 99 \
  -fa on \
  --no-mmap \
  -c 65536 \
  --cache-type-k q4_0 \
  --cache-type-v q4_0 \
  --split-mode layer \
  --tensor-split 1,1 \
  -b 4096 \
  -ub 4096
```

```bash
chmod +x /home/yourusername/start-llm.sh
bash /home/yourusername/start-llm.sh
```

**Key flags:**

| Flag | Value | Purpose |
|---|---|---|
| `-ngl 99` | 99 | Offload all layers to GPU |
| `-fa on` | on | Flash attention — faster, less VRAM |
| `--no-mmap` | — | Do not memory-map the model file — required for multi-GPU splits |
| `-c 65536` | 65,536 | Extended context window |
| `--cache-type-k/v` | q4_0 | Quantised KV cache to save VRAM |
| `--split-mode layer` | layer | Split model layers across GPUs |
| `--tensor-split 1,1` | 1:1 | Equal split between RTX 3090 and Blackwell |
| `-b / -ub` | 4096 | Batch and micro-batch size — faster prefill |

The server exposes an OpenAI-compatible API at `http://<llm-machine-ip>:8080/v1`.

---

## 5. Setting Up the i7

### Prerequisites
- Ubuntu 24.04
- NVIDIA RTX 2060 with CUDA drivers installed (`nvidia-smi` working)
- `git`, `python3`, `uv` installed

### 5.1 Build llama.cpp

```bash
git clone https://github.com/ggerganov/llama.cpp.git /home/yourusername/llama.cpp
cd /home/yourusername/llama.cpp
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release -j$(nproc)
```

Key binaries built to `/home/yourusername/llama.cpp/build/bin/`:
- `llama-server` — used by the `llama-embed` systemd service
- `llama-cli` — interactive CLI for local model testing
- `llama-bench` — benchmarking

### 5.2 Create the llama-embed systemd service

Create `/etc/systemd/system/llama-embed.service`:

```ini
[Unit]
Description=llama.cpp embedding server (nomic-embed-text)
After=network.target

[Service]
Type=simple
User=yourusername
ExecStart=/home/yourusername/llama.cpp/build/bin/llama-server \
  --model /mnt/storage/models/nomic-embed-text-v1.5.Q4_K_M.gguf \
  --port 11435 \
  --host 127.0.0.1 \
  --ctx-size 8192 \
  --batch-size 2048 \
  --embedding \
  --pooling mean \
  --gpu-layers 99 \
  --log-disable
Restart=on-failure
RestartSec=5
Environment=LD_LIBRARY_PATH=/home/yourusername/llama.cpp/build/bin
Environment=ANONYMIZED_TELEMETRY=False

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now llama-embed
```

### 5.3 Set up the MCP tools directory

All scripts and configuration needed are included in this repository under [_python-files/](../_python-files/). Copy the entire folder contents to your machine and restore the virtual environment in one step:

```bash
mkdir -p /mnt/storage/mcp-tools
cp -r /path/to/repo/_python-files/. /mnt/storage/mcp-tools/
cd /mnt/storage/mcp-tools
uv sync
```

`uv sync` reads `uv.lock` and recreates the exact same virtual environment (Python 3.13, pinned package versions). No manual `uv add` required.

The folder contains:

| File | Purpose |
|---|---|
| `config.py` | All configuration constants — edit this to match your machine |
| `proxy.py` | LLM proxy — context enrichment, file watcher |
| `server.py` | MCP context-engine server |
| `docs_server.py` | MCP docs-engine server |
| `index_repos.py` | Repo indexer |
| `index_docs.py` | Documentation indexer |
| `start-services.sh` | Post-reboot health check |
| `update-docs.sh` | Pull and re-index all documentation sources |
| `pyproject.toml` | uv project definition |
| `uv.lock` | Pinned dependency versions |
| `.python-version` | Python version pin (3.13) |

### Configuring for your machine — config.py

All paths, addresses, and tunable settings live in `config.py`. This is the only file you need to edit when setting up on a new machine. The other scripts import from it.

**Paths**

| Constant | Default | Description |
|---|---|---|
| `REPO_ROOT` | `/home/roy/mcp-context/repos` | Root directory where all project repos are checked out |
| `CHROMA_DIR` | `/mnt/storage/chromadb` | Where ChromaDB persists its vector index |
| `DOCS_ROOT` | `/mnt/storage/docs/frameworks` | Root directory for locally cloned documentation libraries |
| `TOOLS_DIR` | `/mnt/storage/mcp-tools` | Path to this tools directory |

**Servers**

| Constant | Default | Description |
|---|---|---|
| `EMBED_URL` | `http://127.0.0.1:11435/v1/embeddings` | Embedding server — runs locally via `llama-embed` |
| `LLM_URL` | `http://192.168.178.99:8080` | LLM inference server on the i9 — used by `proxy.py` only |

**Proxy**

| Constant | Default | Description |
|---|---|---|
| `N_CONTEXT_CHUNKS` | `5` | Number of ChromaDB code chunks injected into each enriched prompt |
| `INDEX_SCRIPT` | derived from `TOOLS_DIR` | Path to `index_repos.py` — called by the proxy's file watcher |
| `VENV_PYTHON` | derived from `TOOLS_DIR` | Path to the virtual environment Python binary |

**Repo file indexing** — used by `index_repos.py` and the proxy file watcher

| Constant | Default | Description |
|---|---|---|
| `INDEXABLE_EXTENSIONS` | `.ts .tsx .js .jsx .css .json` | File types to embed into ChromaDB |
| `EXCLUDED_DIRS` | `node_modules .next dist build .git .venv` | Directories to skip |
| `EXCLUDED_FILES` | `package-lock.json` | Specific files to skip |
| `CHUNK_CHARS` | `600` | Characters per chunk when splitting source files |
| `CHUNK_OVERLAP` | `120` | Overlap between consecutive chunks to preserve context at boundaries |

**Documentation indexing** — used by `index_docs.py`

| Constant | Default | Description |
|---|---|---|
| `DOCS_CHUNK_CHARS` | `800` | Characters per chunk for documentation files (larger than source code) |
| `DOCS_CHUNK_OVERLAP` | `120` | Overlap between documentation chunks |
| `DOCS_EXTENSIONS` | `.md .mdx .txt .d.ts .ts .tsx` etc. | File types to index from documentation sources |
| `DOCS_EXCLUDED_DIRS` | `tr1 ext debug backward decimal profile` | Subdirectories to skip in documentation trees |
| `DOCS_SOURCES` | see `config.py` | Maps each library name to its local file paths — update these after downloading docs |

### 5.4 Build the vector index

With `llama-embed` running (verify with `systemctl status llama-embed`):

```bash
cd /mnt/storage/mcp-tools

# Index the project repo
.venv/bin/python index_repos.py

# Index documentation libraries (run once per library after downloading)
.venv/bin/python index_docs.py --lib nextjs
```

See [ADDING-DOCS.md](ADDING-DOCS.md) for the full indexing process per library. On first run, expect a few minutes per library.

### 5.5 Start the proxy

The proxy must be running before you use Cline. Start it manually after each reboot:

```bash
cd /mnt/storage/mcp-tools
.venv/bin/python proxy.py
```

To stop it: `pkill -f proxy.py`

The proxy logs every request to the terminal — injected chunks, skipped enrichment, and file watcher events are all visible here.

### 5.6 Install the git post-commit hook

This is a safety net that re-indexes the repo after every commit. In normal use the proxy's file watcher handles re-indexing on save, so the hook will usually find nothing new to index. It protects against the case where the proxy was not running when files were saved.

Create `.git/hooks/post-commit` in each repo:

```sh
#!/bin/sh
echo "[post-commit] commit detected — re-indexing..."
/mnt/storage/mcp-tools/.venv/bin/python /mnt/storage/mcp-tools/index_repos.py --repo <reponame> &
echo "[post-commit] re-index started in background"
```

```bash
chmod +x .git/hooks/post-commit
```

### 5.7 Configure Cline on the Mac mini

#### LLM Provider

In VS Code, open the Cline extension panel and go to **Settings**. Configure the provider as follows:

| Setting | Value |
|---|---|
| API Provider | OpenAI Compatible |
| Base URL | `http://<dev-machine-ip>:8000/v1` |
| API Key | any value — e.g. `local` (required by the field but not checked) |
| Model | `qwen2.5-coder-32b-instruct-q4_k_m.gguf` |
| Context window | 65536 |
| Max output tokens | 8096 |

> **Note:** Cline points at the **proxy on the i7** (port 8000), not directly at the i9. The proxy forwards requests to the i9 after enriching them with ChromaDB context. Replace `<dev-machine-ip>` with the IP address of your i7 machine.

#### MCP Servers

Edit:
`/home/yourusername/.vscode-server/data/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

```json
{
  "mcpServers": {
    "context-engine": {
      "disabled": false,
      "timeout": 30,
      "type": "stdio",
      "command": "/mnt/storage/mcp-tools/.venv/bin/python",
      "args": ["/mnt/storage/mcp-tools/server.py"]
    },
    "docs-engine": {
      "disabled": false,
      "timeout": 30,
      "type": "stdio",
      "command": "/mnt/storage/mcp-tools/.venv/bin/python",
      "args": ["/mnt/storage/mcp-tools/docs_server.py"]
    }
  }
}
```

This file tells Cline how to launch each MCP server when VS Code starts. Cline reads it on
startup and spawns each server as a child process, communicating over stdin/stdout — not over
a network socket. The servers only exist while VS Code is open; Cline starts and stops them
automatically.

The setup uses two separate servers rather than one. This keeps the number of tools per server
small, which reduces the length of the system prompt Cline sends to the LLM and makes it
easier for the model to generate correctly formatted tool calls.

**context-engine entry:**
Runs `server.py` — the repo search server with 5 tools: `list_repos`, `read_repo_file`,
`search_official_docs`, `read_doc_page`, and `semantic_search`.

**docs-engine entry:**
Runs `docs_server.py` — the documentation search server with 3 tools, one per indexed library:
`search_nextjs_docs`, `search_react_docs`, and `search_typescript_docs`.

**Why `.venv/bin/python` rather than `uv run`:**
Calling `.venv/bin/python` directly starts the server immediately — the virtual environment is
already activated. Using `uv run` instead causes `uv` to re-resolve the environment on every
VS Code launch, which adds a significant cold-start delay. Direct invocation avoids this
entirely.

> **Note:** Replace `/mnt/storage/mcp-tools/` with the path to your own MCP tools directory.

---

## 6. After a Reboot

### i9
The LLM does not start automatically. SSH into the i9 and run:

```bash
bash /home/yourusername/start-llm.sh
```

### i7
The `llama-embed` service starts automatically. Start the proxy manually:

```bash
cd /mnt/storage/mcp-tools
.venv/bin/python proxy.py
```

To verify everything is healthy:

```bash
bash /mnt/storage/mcp-tools/start-services.sh
```

Then open VS Code — Cline will launch both MCP servers automatically.

**Startup order:** i9 LLM → i7 proxy → VS Code / Cline. Cline must point at the proxy, not the i9 directly.

---

## 7. Python Scripts

There are five Python files in `/mnt/storage/mcp-tools/`. They each have a distinct role but
share the same infrastructure — the embedding server on the i7 and the ChromaDB store on disk.
Copies of all five are included in this repo under [_python-files/](../_python-files/).

---

### server.py — The context-engine MCP Server (always running)

**What it is:** A FastMCP server that Cline talks to directly. It is not a script you run
manually — Cline launches it automatically every time VS Code starts.

**What it does:**

It exposes 5 tools to Cline for repo access and search. When Cline calls one of these tools, `server.py` handles the request:

- For **keyword search** (`search_official_docs`) it shells out to `ripgrep` and returns the raw matches.
- For **file reads** (`read_repo_file`, `read_doc_page`) it opens the file directly and returns the content.
- For **semantic search** (`semantic_search`) it sends the query to `llama-server` on port 11435 (RTX 2060) to get a vector embedding, then queries ChromaDB for the closest matching chunks, and returns the results.
- For **repo listing** (`list_repos`) it scans the repos directory and returns the folder names.

**Connections made at runtime:**

| Destination | Address | Purpose |
|---|---|---|
| llama-embed (RTX 2060) | `http://127.0.0.1:11435` | Embed queries into vectors (localhost on dev machine) |
| ChromaDB | `/mnt/storage/chromadb/` | Vector similarity search |

---

### docs_server.py — The docs-engine MCP Server (always running)

**What it is:** A second FastMCP server, also launched automatically by Cline. It is kept separate from `server.py` to keep each server's tool count small, which makes it easier for the LLM to generate correctly formatted tool calls.

**What it does:**

It exposes three semantic search tools:

- `search_nextjs_docs` — Next.js routing, data fetching, API routes, and configuration
- `search_react_docs` — React documentation
- `search_typescript_docs` — TypeScript handbook and tsconfig reference

Each tool sends the query to `llama-server` on port 11435 to get a vector embedding, then queries the corresponding ChromaDB collection, and returns matching snippets with file path, line range, and similarity score.

See [ADDING-DOCS.md](ADDING-DOCS.md) for how to add further libraries and wire up their tools.

**Connections made at runtime:**

| Destination | Address | Purpose |
|---|---|---|
| llama-embed (RTX 2060) | `http://127.0.0.1:11435` | Embed queries into vectors (localhost on dev machine) |
| ChromaDB | `/mnt/storage/chromadb/` | Vector similarity search |

---

### index_repos.py — Project Code Indexer

**What it is:** A one-shot script that scans your project repo source files and builds the
ChromaDB vector index. You never call it directly in normal use — the git post-commit hook
calls it automatically in the background after every commit.

**What it does:**

1. Walks the repo directory, skipping `node_modules`, `.next`, `build`, `.git`, etc.
2. For each `.ts`, `.tsx`, `.js`, `.css`, `.json`, `.md` file it computes a SHA-256 hash and
   compares it to the stored hash in `index_manifest.json`.
3. **If the file is unchanged, it skips it.** This is why incremental runs are fast.
4. For changed files it splits the content into overlapping 600-character chunks (with a 120-
   character overlap so context is not lost at chunk boundaries).
5. Sends each chunk to `llama-server` on port 11435 to get a 768-dimension vector embedding.
6. Upserts the chunks, embeddings, and metadata (file path, line numbers) into ChromaDB under
   the collection `repo_<reponame>`.
7. Saves the updated hash manifest so the next run knows what has already been indexed.
8. If a file has been deleted from the repo, it removes that file's chunks from ChromaDB too.

**Connections made at runtime:**

| Destination | Address | Purpose |
|---|---|---|
| llama-embed (RTX 2060) | `http://127.0.0.1:11435` | Embed code chunks |
| ChromaDB | `/mnt/storage/chromadb/` | Store vectors |

---

### index_docs.py — Documentation Indexer

**What it is:** The same idea as `index_repos.py` but for third-party documentation libraries
rather than your own code. Run manually via `update-docs.sh` after pulling a docs update.

**What it does:**

1. Reads `DOCS_SOURCES` — a dictionary mapping each library name (e.g. `nextjs`)
   to a list of file paths or directories to walk.
2. For each file it hashes, chunks (800-character chunks with 120-character overlap), embeds,
   and upserts into ChromaDB under the collection `docs_<libname>`.
3. Saves progress to `docs_manifest.json` after **each individual file** — so if indexing is
   interrupted partway through a large library, the next run picks up where it left off rather
   than starting over.
4. Embeds in batches of 4 chunks at a time; if a batch fails (chunk too large for the embedding
   server), it falls back to embedding one chunk at a time.

**Connections made at runtime:**

| Destination | Address | Purpose |
|---|---|---|
| llama-embed (RTX 2060) | `http://127.0.0.1:11435` | Embed documentation chunks |
| ChromaDB | `/mnt/storage/chromadb/` | Store vectors |

---

### proxy.py — LLM Proxy with Context Enrichment (always running)

**What it is:** A FastAPI server on the i7 (port 8000) that sits between Cline and the i9 LLM. You start it manually after a reboot and leave it running.

**What it does:**

Every `/v1/chat/completions` request from Cline passes through the proxy:

1. Scans the conversation history to detect which repo is being worked on (by matching repo directory names found in message content)
2. If the prompt contains `src/`, enrichment is **skipped** — Cline reads the file directly via the MCP server, which gives the model clean file content for reliable SEARCH/REPLACE edits
3. Otherwise, it embeds the user's prompt and queries ChromaDB for the 5 most relevant code chunks from that repo
4. Injects the chunks into the prompt before forwarding to the i9
5. Streams the response back to Cline

It also runs a **file watcher** (watchdog) over all repos under `REPO_ROOT`. When any tracked file (`.ts`, `.tsx`, `.js`, `.jsx`, `.css`, `.json`) is saved, it schedules a re-index of that repo after a 3-second debounce. Each repo has its own independent debounce timer.

A `/reindex` endpoint allows forcing a re-index from the terminal:

```bash
# Re-index a specific repo
curl -X POST http://localhost:8000/reindex?repo=stoodleyweather

# Re-index all repos
curl -X POST http://localhost:8000/reindex
```

**Connections made at runtime:**

| Destination | Address | Purpose |
|---|---|---|
| llama-embed (RTX 2060) | `http://127.0.0.1:11435` | Embed queries into vectors |
| ChromaDB | `/mnt/storage/chromadb/` | Retrieve relevant code chunks |
| i9 LLM | `http://<llm-machine-ip>:8080` | Forward enriched requests |

---

### How the five scripts relate

```
index_repos.py  ─┐
                 ├──► llama-embed (port 11435, RTX 2060) ──► ChromaDB (/mnt/storage/chromadb/)
index_docs.py   ─┘                                               │
                                                        ┌────────┴────────┐
                                                        │                 │
                                               proxy.py reads        server.py reads
                                               ChromaDB (enrichment) ChromaDB (repo search)
                                               also calls            also calls
                                               llama-embed           llama-embed
                                                        │                 │
                                                   Cline (all requests) Cline (read_repo_file)
```

The two indexing scripts **write** to ChromaDB. `proxy.py`, `server.py`, and `docs_server.py` **read** from ChromaDB.
All five scripts use the same embedding server on port 11435 — the indexers to embed source content,
and the servers to embed incoming queries so they can be compared against the stored vectors.

---

## 8. Reference

### MCP Tools

Two FastMCP servers provide all tools to Cline. For a full set of example prompts for every tool, see [CLINE-PROMPTS.md](CLINE-PROMPTS.md).

**context-engine** — `server.py`

| Tool | Description |
|---|---|
| `list_repos` | Lists available repos under `/mnt/storage/mcp-context/repos/` |
| `read_repo_file` | Reads a specific file from a repo |
| `search_official_docs` | Searches local React documentation via ripgrep |
| `read_doc_page` | Reads a specific doc page |
| `semantic_search` | Natural language / vector search over a repo (uses RTX 2060) |

**docs-engine** — `docs_server.py`

| Tool | Description |
|---|---|
| `search_nextjs_docs` | Semantic search over Next.js documentation — routing, data fetching, API routes |
| `search_react_docs` | Semantic search over React documentation |
| `search_typescript_docs` | Semantic search over TypeScript handbook and tsconfig reference |

Add further tools by following the process in [ADDING-DOCS.md](ADDING-DOCS.md).

### Documentation Libraries

Documentation sources are cloned locally and indexed into ChromaDB so that Cline can search them semantically — meaning you can ask questions like "how do I fetch data in a server component" and get accurate answers pulled directly from the source documentation, without leaving the editor.

| Library / Framework | Language | Use | Source | How downloaded |
|---|---|---|---|---|
| React 19 | TypeScript | Web UI framework | `github.com/reactjs/react.dev` | `git clone` |
| TypeScript | TypeScript | Language reference and compiler options | `github.com/microsoft/TypeScript-Website` | `git sparse-clone` |
| Next.js | TypeScript | React framework — routing, server components, API routes | `github.com/vercel/next.js` | `git sparse-clone` (docs/ only) |

Add further libraries by following the process in [ADDING-DOCS.md](ADDING-DOCS.md).

### ChromaDB Collections

| Collection | Source |
|---|---|
| `repo_stoodleyweather` | Source code — auto-updated on file save and commit |
| `docs_nextjs` | Next.js docs (git sparse clone) |
| `docs_react` | React docs (git clone) |
| `docs_typescript` | TypeScript handbook + tsconfig reference (git sparse clone) |

Each library you add via [ADDING-DOCS.md](ADDING-DOCS.md) creates a new `docs_<name>` collection.

### LLM Properties

| Property | Value |
|---|---|
| Model | Qwen2.5-Coder-32B-Instruct |
| Quantisation | Q8_0 |
| Parameters | 32.7B |
| File | `/home/yourusername/models/Qwen2.5-Coder-32B-Instruct-Q8_0.gguf` |
| Context window | 65,536 tokens |
| KV cache | Q4_0 quantised |
| Flash attention | enabled |
| GPU split | 1:1 layer-based across RTX 3090 and Blackwell |
| Endpoint | `http://<llm-machine-ip>:8080/v1` |

### Embedding Model Properties

| Property | Value |
|---|---|
| Model | nomic-embed-text-v1.5 |
| Quantisation | Q4_K_M |
| File | `/mnt/storage/models/nomic-embed-text-v1.5.Q4_K_M.gguf` |
| Context window | 8,192 tokens |
| Dimensions | 768 |
| Host | i7 (RTX 2060) |
| Port | 11435 |

### Directory Structure (i7 /mnt/storage/)

```
/mnt/storage/
├── models/
│   └── nomic-embed-text-v1.5.Q4_K_M.gguf
├── chromadb/                        # Persisted vector index (~516MB)
│   ├── index_manifest.json          # Repo file hash manifest
│   └── docs_manifest.json           # Docs file hash manifest
├── mcp-tools/
│   ├── proxy.py                     # LLM proxy — context enrichment, file watcher (port 8000)
│   ├── server.py                    # MCP context-engine server (FastMCP)
│   ├── docs_server.py               # MCP docs-engine server (FastMCP)
│   ├── index_repos.py               # Repo indexing script
│   ├── index_docs.py                # Docs indexing script
│   ├── start-services.sh            # Post-reboot health check script
│   ├── update-docs.sh               # Update and re-index all docs
│   ├── pyproject.toml
│   └── .venv/
├── docs/
│   └── frameworks/
│       ├── react-docs/
│       ├── typescript-docs/
│       └── nextjs-docs/
└── mcp-context/
    └── repos/
        └── stoodleyweather/           # Next.js weather app
```

### Systemd Services (i7)

| Service | Description | Auto-start |
|---|---|---|
| `llama-embed` | Embedding server on RTX 2060, port 11435 | Yes |

```bash
systemctl status llama-embed
sudo systemctl start llama-embed
sudo systemctl stop llama-embed
journalctl -u llama-embed -f
```

### Re-indexing

When you write or change code, the ChromaDB vector index needs to reflect those changes —
otherwise semantic search would be querying stale embeddings and returning results that no
longer match the actual codebase.

Re-indexing works by scanning each source file, computing a SHA-256 hash of its contents, and
comparing that hash against a manifest saved from the previous run. Only files whose hash has
changed are re-embedded and re-inserted into ChromaDB. This makes incremental runs fast — on
a typical save it processes one or two files rather than the entire codebase.

**Primary trigger — file watcher:** `proxy.py` runs a watchdog file watcher over all repos
under `REPO_ROOT`. When a file is saved in VS Code, the watcher detects the change, waits 3
seconds (debounce), and re-indexes that repo. ChromaDB is therefore always in sync with the
current file contents — not just what was last committed. The re-index log appears in the
proxy terminal.

**Safety net — post-commit hook:** A `post-commit` hook in each repo calls `index_repos.py`
after every commit. In normal use the watcher has already indexed the latest file contents,
so the hook finds nothing new and outputs `Done. 0 chunks indexed` — this is correct behaviour,
not an error. It protects against the case where the proxy was not running when files were saved.

Documentation libraries (Next.js, React, TypeScript) do not change automatically because
they are external sources — their docs only change when you pull an update. Those are
re-indexed manually by running `update-docs.sh`.

Manual re-indexing is only needed in specific cases:

| Command | When to use |
|---|---|
| `curl -X POST http://localhost:8000/reindex?repo=stoodleyweather` | Force re-index via proxy (proxy must be running) |
| `curl -X POST http://localhost:8000/reindex` | Re-index all repos via proxy |
| `python index_repos.py --repo stoodleyweather` | Re-index without the proxy running |
| `python index_repos.py --full` | After changing the embedding model or chunk size |
| `bash update-docs.sh` | After updating all documentation sources |
| `python index_docs.py --lib nextjs` | Single docs library only |

---

## Sharing

If you found this useful and want to share it on social media, suggested hashtags:

```
#LocalLLM #HomeLab #AISetup #LlamaCpp #Qwen2 #OpenSource #SelfHosted
#SemanticSearch #RAG #ChromaDB #NVIDIA #CodingAssistant #AITools
#Ubuntu #CUDA #VSCode #Cline #MCP #DeveloperTools #AIAssistant
```

