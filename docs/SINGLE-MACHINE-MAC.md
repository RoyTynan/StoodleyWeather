# Single Machine Setup — Apple Silicon Mac

This document covers how to run the full AI development setup described in [AI-SETUP.md](AI-SETUP.md) on a single Apple Silicon Mac with at least 64GB of unified memory.

No second machine is needed. The LLM, embedding server, proxy, and MCP servers all run on the same Mac.

> **Heat warning:** Running a 32B parameter model on a MacBook Pro will cause sustained high CPU/GPU load. The machine will get hot, the fans will run continuously, and on battery you will see significant drain. On a Mac mini or Mac Studio this is less of a concern. If you are on a laptop, keep it plugged in and on a hard surface with good airflow.

---

## Why 64GB

The model used in this setup — `Qwen2.5-Coder-32B-Instruct-Q8_0` — occupies approximately 34.8GB. Apple Silicon uses unified memory shared between CPU and GPU (Neural Engine), so the model, KV cache, OS, and all running processes compete for the same pool.

| Allocation | Approximate size |
|---|---|
| Model (Q8_0) | ~35GB |
| KV cache (at 65K context) | ~4–6GB |
| OS + apps + VS Code | ~8–12GB |
| Embedding model | ~0.5GB |
| Headroom | remainder |

64GB is the minimum comfortable size. 96GB or 128GB gives more headroom for larger context and parallel processes.

If you have exactly 64GB and find it tight, switch to `Qwen2.5-Coder-32B-Instruct-Q4_K_M` (~18GB) at the cost of some output quality.

---

## Differences from the multi-machine setup

| Aspect | Multi-machine | Single Mac |
|---|---|---|
| LLM backend | CUDA (NVIDIA) | Metal (Apple Silicon) |
| Machines | 3 (Mac, i7, i9) | 1 |
| GPU split | `--split-mode layer` across 2 GPUs | Not needed |
| Network addresses | LAN IPs | `127.0.0.1` / `localhost` throughout |
| Systemd services | Yes (Linux) | launchd or manual startup |
| llama.cpp build flags | `-DGGML_CUDA=ON` | `-DGGML_METAL=ON` |

---

## 1. Install prerequisites

```bash
# Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Dependencies
brew install git python3 cmake ripgrep

# uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 2. Build llama.cpp with Metal

```bash
git clone https://github.com/ggerganov/llama.cpp.git ~/llama.cpp
cd ~/llama.cpp
cmake -B build -DGGML_METAL=ON
cmake --build build --config Release -j$(sysctl -n hw.logicalcpu)
```

Metal support is built in by default on Apple Silicon — no driver installation required.

---

## 3. Download the models

### LLM

```bash
mkdir -p ~/models
wget --header="Authorization: Bearer your-huggingface-token" \
    https://huggingface.co/bartowski/Qwen2.5-Coder-32B-Instruct-GGUF/resolve/main/Qwen2.5-Coder-32B-Instruct-Q8_0.gguf \
    -O ~/models/Qwen2.5-Coder-32B-Instruct-Q8_0.gguf \
    --continue --progress=dot:giga
```

If 64GB feels tight at runtime, use the smaller quantisation instead:

```bash
wget --header="Authorization: Bearer your-huggingface-token" \
    https://huggingface.co/bartowski/Qwen2.5-Coder-32B-Instruct-GGUF/resolve/main/Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf \
    -O ~/models/Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf \
    --continue --progress=dot:giga
```

### Embedding model

```bash
python3 -c "
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id='BAAI/bge-m3-GGUF',
    filename='bge-m3-Q8_0.gguf',
    local_dir='$HOME/models/'
)"
```

---

## 4. Create the startup script

Create `~/start-llm.sh`:

```bash
#!/bin/bash
pkill llama-server
sleep 2

SERVER_BIN="$HOME/llama.cpp/build/bin/llama-server"
MODEL_PATH="$HOME/models/Qwen2.5-Coder-32B-Instruct-Q8_0.gguf"

$SERVER_BIN \
  -m "$MODEL_PATH" \
  --host 127.0.0.1 \
  --port 8080 \
  -ngl 99 \
  -fa on \
  -c 65536 \
  --cache-type-k q4_0 \
  --cache-type-v q4_0 \
  -b 2048 \
  -ub 2048
```

```bash
chmod +x ~/start-llm.sh
```

**Key differences from the Linux/CUDA script:**
- `--host 127.0.0.1` — localhost only, no LAN exposure needed
- No `--split-mode` or `--tensor-split` — single GPU
- No `--no-mmap` — not required on Metal
- `-ngl 99` — still valid; offloads all layers to Metal GPU

> **Note on `-b` / `-ub`:** Batch size affects how fast the model processes the prompt (prefill speed). Higher values are faster but use more memory. Start at 2048 and reduce if you see memory pressure.

---

## 5. Set up the embedding server

The embedding server needs to run on a separate port from the LLM. Create `~/start-embed.sh`:

```bash
#!/bin/bash
pkill -f "llama-server.*11435"
sleep 1

$HOME/llama.cpp/build/bin/llama-server \
  --model $HOME/models/bge-m3-Q8_0.gguf \
  --port 11435 \
  --host 127.0.0.1 \
  --ctx-size 8192 \
  --batch-size 2048 \
  --embedding \
  --pooling mean \
  --gpu-layers 99 \
  --log-disable
```

```bash
chmod +x ~/start-embed.sh
```

On macOS there is no systemd. You can either run this manually in a terminal or create a launchd service. To run manually:

```bash
bash ~/start-embed.sh &
```

---

## 6. Set up the MCP tools

```bash
mkdir -p ~/mcp-tools
cp -r /path/to/repo/_python-files/. ~/mcp-tools/
cd ~/mcp-tools
uv sync
```

`uv sync` recreates the exact virtual environment from `uv.lock`. No manual `uv add` required.

### Update config.py for your Mac

All configuration is in `config.py` — this is the only file you need to edit. Replace the Linux paths and the LAN IP with your own Mac paths. Everything runs on `127.0.0.1` since it is a single machine.

| Constant | Change to |
|---|---|
| `REPO_ROOT` | `/Users/yourusername/repos` |
| `CHROMA_DIR` | `/Users/yourusername/mcp-tools/chromadb` |
| `DOCS_ROOT` | `/Users/yourusername/docs/frameworks` |
| `TOOLS_DIR` | `/Users/yourusername/mcp-tools` |
| `LLM_URL` | `http://127.0.0.1:8080` |
| `EMBED_URL` | `http://127.0.0.1:11435/v1/embeddings` (no change needed) |

`DOCS_SOURCES` in `config.py` also contains paths — update each entry to match where you cloned the documentation libraries on your Mac.

---

## 7. Index your repo

With the embedding server running:

```bash
cd ~/mcp-tools
.venv/bin/python index_repos.py --repo yourreponame
```

---

## 8. Install the git post-commit hook

In each repo:

```bash
cat > .git/hooks/post-commit << 'EOF'
#!/bin/sh
echo "[post-commit] re-indexing..."
$HOME/mcp-tools/.venv/bin/python $HOME/mcp-tools/index_repos.py --repo yourreponame &
EOF
chmod +x .git/hooks/post-commit
```

---

## 9. Configure Cline

In VS Code, configure the Cline provider:

| Setting | Value |
|---|---|
| API Provider | OpenAI Compatible |
| Base URL | `http://127.0.0.1:8000/v1` |
| API Key | `local` |
| Model | `qwen2.5-coder-32b-instruct-q8_0.gguf` |
| Context window | 65536 |
| Max output tokens | 8096 |

MCP settings file — `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`:

```json
{
  "mcpServers": {
    "context-engine": {
      "disabled": false,
      "timeout": 30,
      "type": "stdio",
      "command": "/Users/yourusername/mcp-tools/.venv/bin/python",
      "args": ["/Users/yourusername/mcp-tools/server.py"]
    },
    "docs-engine": {
      "disabled": false,
      "timeout": 30,
      "type": "stdio",
      "command": "/Users/yourusername/mcp-tools/.venv/bin/python",
      "args": ["/Users/yourusername/mcp-tools/docs_server.py"]
    }
  }
}
```

---

## 10. After a reboot

Open three terminal tabs and run in order:

```bash
# Tab 1 — embedding server
bash ~/start-embed.sh

# Tab 2 — LLM
bash ~/start-llm.sh

# Tab 3 — proxy
cd ~/mcp-tools && .venv/bin/python proxy.py
```

Then open VS Code. Cline will launch the MCP servers automatically.

> **Tip:** If the machine becomes unresponsive or the fans are very loud, check Activity Monitor → GPU History and Memory Pressure. If memory pressure is high (red), reduce the context window in Cline settings from 65536 to 32768, or switch to the Q4_K_M model.

---

## Summary of all addresses (single machine)

| Service | Address |
|---|---|
| LLM server | `http://127.0.0.1:8080` |
| Embedding server | `http://127.0.0.1:11435` |
| Proxy (Cline points here) | `http://127.0.0.1:8000` |
