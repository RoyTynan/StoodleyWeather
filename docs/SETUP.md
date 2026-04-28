# Setup Guide

Step-by-step installation for the three-machine setup: i9 (LLM), i7 (proxy + embeddings), Mac mini (VS Code client). For single-machine variants see [SINGLE-MACHINE-LINUX.md](SINGLE-MACHINE-LINUX.md), [SINGLE-MACHINE-MAC.md](SINGLE-MACHINE-MAC.md), or [SINGLE-MACHINE-WINDOWS.md](SINGLE-MACHINE-WINDOWS.md).

> **Path conventions:** `/mnt/storage/` is the storage mount on the i7. IP addresses (`192.168.178.x`) are specific to this network. Replace both with your own values throughout.

---

## Machines

| Machine | Role | Key hardware |
|---|---|---|
| Mac mini | Thin client — VS Code only | — |
| i7 Ubuntu | Proxy, embeddings, MCP servers, monitor | RTX 2060 (6GB VRAM) |
| i9 Ubuntu | LLM inference | RTX 3090 + Blackwell PRO 4000 = 48GB VRAM |

---

## 1. Downloads

### i9 — LLM model

> **Current model:** Qwen3.6-35B-A3B-Q8_0 (updated April 2026). See [LLM-QWEN3.md](LLM-QWEN3.md) for download and startup details.

The original model used during initial setup:

```bash
wget --header="Authorization: Bearer your-huggingface-token" \
    https://huggingface.co/bartowski/Qwen2.5-Coder-32B-Instruct-GGUF/resolve/main/Qwen2.5-Coder-32B-Instruct-Q8_0.gguf \
    -O /home/yourusername/models/Qwen2.5-Coder-32B-Instruct-Q8_0.gguf \
    --continue --progress=dot:giga
```

`--continue` allows resuming an interrupted download.

### i7 — Embedding model

```bash
python3 -c "
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id='BAAI/bge-m3-GGUF',
    filename='bge-m3-Q8_0.gguf',
    local_dir='/mnt/storage/models/'
)"
```

### i7 — Documentation sources (optional)

```bash
# React docs
git clone https://github.com/reactjs/react.dev.git /mnt/storage/docs/frameworks/react-docs

# TypeScript docs (handbook and tsconfig reference only)
git clone --depth=1 --filter=blob:none --sparse https://github.com/microsoft/TypeScript-Website.git /mnt/storage/docs/frameworks/typescript-docs
git -C /mnt/storage/docs/frameworks/typescript-docs sparse-checkout set packages/documentation/copy/en packages/tsconfig-reference

# Next.js docs (docs/ only)
git clone --depth=1 --filter=blob:none --sparse https://github.com/vercel/next.js.git /mnt/storage/docs/frameworks/nextjs-docs
git -C /mnt/storage/docs/frameworks/nextjs-docs sparse-checkout set docs
```

See [ADDING-DOCS.md](ADDING-DOCS.md) for indexing each library into ChromaDB.

---

## 2. Setting Up the i9

**Prerequisites:** Ubuntu 24.04, NVIDIA drivers + CUDA (`nvidia-smi` working for both GPUs), `git`

### Build llama.cpp

```bash
git clone https://github.com/ggerganov/llama.cpp.git /home/yourusername/llama.cpp
cd /home/yourusername/llama.cpp
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release -j$(nproc)
```

### Create start-llm.sh

> **Current config:** see [LLM-QWEN3.md](LLM-QWEN3.md) for the updated startup script for Qwen3.6-35B-A3B.

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

| Flag | Purpose |
|---|---|
| `-ngl 99` | Offload all layers to GPU |
| `-fa on` | Flash attention — faster, less VRAM |
| `--no-mmap` | Required for multi-GPU splits |
| `-c 65536` | 65K context window |
| `--cache-type-k/v q4_0` | Quantised KV cache to save VRAM |
| `--split-mode layer` | Split model layers across GPUs |
| `--tensor-split 1,1` | Equal split between RTX 3090 and Blackwell |
| `-b / -ub 4096` | Batch size — faster prefill |

The server exposes an OpenAI-compatible API at `http://<i9-ip>:8080/v1`.

---

## 3. Setting Up the i7

**Prerequisites:** Ubuntu 24.04, NVIDIA RTX 2060 with CUDA (`nvidia-smi` working), `git`, `python3`, `uv`

### Build llama.cpp

```bash
git clone https://github.com/ggerganov/llama.cpp.git /home/yourusername/llama.cpp
cd /home/yourusername/llama.cpp
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release -j$(nproc)
```

### Create the llama-embed systemd service

Create `/etc/systemd/system/llama-embed.service`:

```ini
[Unit]
Description=llama.cpp embedding server (bge-m3)
After=network.target

[Service]
Type=simple
User=yourusername
ExecStart=/home/yourusername/llama.cpp/build/bin/llama-server \
  --model /mnt/storage/models/bge-m3-Q8_0.gguf \
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

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now llama-embed
```

### Set up the MCP tools directory

```bash
cp -r /path/to/stoodleyweather/_python-files /mnt/storage/mcp-tools
cd /mnt/storage/mcp-tools
uv sync
```

`uv sync` recreates the exact virtual environment from `uv.lock`. No manual package installs needed.

### Configure config.py

Edit `/mnt/storage/mcp-tools/config.py` — this is the only file you need to change for a new machine:

**Paths**

| Constant | Default | Description |
|---|---|---|
| `REPO_ROOT` | `/home/roy/mcp-context/repos` | Where all project repos are checked out |
| `CHROMA_DIR` | `/mnt/storage/chromadb` | Where ChromaDB persists its index |
| `DOCS_ROOT` | `/mnt/storage/docs/frameworks` | Root for documentation libraries |
| `TOOLS_DIR` | `/mnt/storage/mcp-tools` | Path to this directory |

**Servers**

| Constant | Default | Description |
|---|---|---|
| `EMBED_URL` | `http://127.0.0.1:11435/v1/embeddings` | Embedding server (llama-embed) |
| `LLM_URL` | `http://192.168.178.99:8080` | LLM inference server on the i9 |

**Proxy tuning**

| Constant | Default | Description |
|---|---|---|
| `N_CONTEXT_CHUNKS` | `5` | Code chunks injected per prompt |
| `SKELETON_MAX_FILES` | `60` | Max files in the codebase skeleton map |
| `CHUNK_CHARS` | `600` | Characters per chunk |
| `CHUNK_OVERLAP` | `120` | Overlap between chunks |
| `LLM_HAS_THINKING` | `True` | Set `True` for models with thinking mode (Qwen3, DeepSeek-R1). Disables think blocks in requests and strips `<think>` tags from responses. Set `False` for Qwen2.5, Llama, etc. |

**Dependency graph**

| Constant | Default | Description |
|---|---|---|
| `DEP_GRAPH_ENABLED` | `True` | Enable import-edge analysis — injects impact warnings when an edited file is imported by others |
| `MAX_IMPACT_FILES` | `5` | Maximum dependent files to list per edit |

### Build the vector index

With `llama-embed` running (`systemctl status llama-embed`):

```bash
cd /mnt/storage/mcp-tools

# Index all repos
.venv/bin/python index_repos.py

# Index documentation (once per library)
.venv/bin/python index_docs.py --lib nextjs
.venv/bin/python index_docs.py --lib react
.venv/bin/python index_docs.py --lib typescript
```

### Start the proxy

```bash
bash /mnt/storage/mcp-tools/start-proxy.sh
```

The proxy must be running before using Cline. Start it manually after each reboot. It logs every request to the terminal — injected chunks, file watcher events, and HALT notifications.

To stop: `pkill -f proxy.py`

### Increase inotify watch limit

The proxy file watcher needs a higher inotify limit than the Ubuntu default:

```bash
echo "fs.inotify.max_user_watches=524288" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p
```

This survives reboots.

### Install the git post-commit hook

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

This is a safety net — the file watcher handles re-indexing on save, but this covers the case where the proxy wasn't running when files were changed.

---

## 4. Configuring Cline

In VS Code, open the Cline extension settings:

| Setting | Value |
|---|---|
| API Provider | OpenAI Compatible |
| Base URL | `http://<i7-ip>:8000/v1` (the proxy — not the i9 directly) |
| API Key | any value — e.g. `local` |
| Model | `Qwen3.6-35B-A3B-Q8_0.gguf` — see [LLM-QWEN3.md](LLM-QWEN3.md) |
| Context window | `102400` |
| Max output tokens | 8096 |
| Native Tool Calling | Off |
| Parallel Tool Calling | Off |

### MCP Servers

Edit:
`~/.vscode-server/data/User/globalStorage/roytynan.cline-roy/settings/cline_mcp_settings.json`

> If `roytynan.cline-roy` doesn't exist, check for `saoudrizwan.claude-dev`.

```json
{
  "mcpServers": {
    "context-engine": {
      "disabled": false,
      "timeout": 30,
      "type": "stdio",
      "command": "ssh",
      "args": [
        "yourusername@<i7-ip>",
        "/mnt/storage/mcp-tools/.venv/bin/python",
        "/mnt/storage/mcp-tools/server.py"
      ]
    },
    "docs-engine": {
      "disabled": false,
      "timeout": 30,
      "type": "stdio",
      "command": "ssh",
      "args": [
        "yourusername@<i7-ip>",
        "/mnt/storage/mcp-tools/.venv/bin/python",
        "/mnt/storage/mcp-tools/docs_server.py"
      ]
    }
  }
}
```

Cline launches both MCP servers automatically when VS Code starts. They communicate over stdin/stdout via SSH — no extra network ports needed.

---

## 5. After a Reboot

**i9:**
```bash
bash /home/yourusername/start-llm.sh
```

**i7:**
```bash
bash /mnt/storage/mcp-tools/start-proxy.sh
```

`llama-embed` starts automatically via systemd. Open VS Code — Cline starts both MCP servers automatically.

To verify everything is healthy:
```bash
bash /mnt/storage/mcp-tools/start-services.sh
```

**Startup order:** i9 LLM → i7 proxy → VS Code.
