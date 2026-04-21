# Single Machine Setup — Linux (NVIDIA GPU)

This document covers how to run the full AI development setup described in [AI-SETUP.md](AI-SETUP.md) on a single Linux machine with an NVIDIA GPU and at least 16GB of VRAM.

No second machine is needed. The LLM, embedding server, proxy, and MCP servers all run on the same machine.

> **Heat warning:** Running a large language model under sustained load will push your GPU to high temperatures. Ensure your case has adequate airflow and your GPU cooler is clean. On a laptop, keep it plugged in and on a hard surface.

---

## Prerequisites

- Ubuntu 22.04 or 24.04 (other distros will work with minor adjustments)
- NVIDIA GPU with CUDA support (GTX 10 series or newer)
- NVIDIA drivers and CUDA toolkit installed (`nvidia-smi` working)
- At least 16GB VRAM — see [GPU-MODELS.md](GPU-MODELS.md) for model recommendations by VRAM size

---

## Differences from the multi-machine setup

| Aspect | Multi-machine | Single Linux |
|---|---|---|
| Machines | 3 (Mac, i7, i9) | 1 |
| GPU split | `--split-mode layer` across 2 GPUs | Not needed |
| Network addresses | LAN IPs | `127.0.0.1` / `localhost` throughout |
| Embedding server | Separate machine (i7) | Same machine, different port |
| VS Code | Remote SSH from Mac | Local or Remote SSH from another machine |
| llama.cpp build flags | `-DGGML_CUDA=ON` | `-DGGML_CUDA=ON` (identical) |

The setup is essentially the same as the multi-machine version — just collapsed onto one machine with everything on localhost.

---

## 1. Install prerequisites

```bash
sudo apt update
sudo apt install -y git cmake build-essential python3 python3-pip ripgrep curl
```

### NVIDIA drivers and CUDA

If not already installed:

```bash
# Check if drivers are working
nvidia-smi

# If not, install drivers (adjust version to match your GPU)
sudo apt install -y nvidia-driver-560

# Install CUDA toolkit
sudo apt install -y nvidia-cuda-toolkit
```

Reboot after installing drivers.

### uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

---

## 2. Build llama.cpp with CUDA

```bash
git clone https://github.com/ggerganov/llama.cpp.git ~/llama.cpp
cd ~/llama.cpp
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release -j$(nproc)
```

---

## 3. Download the models

### LLM

```bash
mkdir -p ~/models
wget --header="Authorization: Bearer your-huggingface-token" \
    https://huggingface.co/bartowski/Qwen2.5-Coder-32B-Instruct-GGUF/resolve/main/Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf \
    -O ~/models/Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf \
    --continue --progress=dot:giga
```

Choose the quantisation that fits your VRAM — see [GPU-MODELS.md](GPU-MODELS.md). The Q4_K_M (~18.5GB) is a good starting point for a 24GB card.

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
MODEL_PATH="$HOME/models/Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf"

$SERVER_BIN \
  -m "$MODEL_PATH" \
  --host 127.0.0.1 \
  --port 8080 \
  -ngl 99 \
  -fa on \
  --no-mmap \
  -c 65536 \
  --cache-type-k q4_0 \
  --cache-type-v q4_0 \
  -b 2048 \
  -ub 2048
```

```bash
chmod +x ~/start-llm.sh
```

- `--host 127.0.0.1` — localhost only, no LAN exposure needed
- No `--split-mode` or `--tensor-split` — single GPU
- `--no-mmap` — required for CUDA single-GPU stability

> **Note on `-b` / `-ub`:** Start at 2048. If VRAM allows, increase to 4096 for faster prompt prefill.

---

## 5. Set up the embedding server as a systemd service

The embedding server runs on a separate port and starts automatically on boot.

Create `/etc/systemd/system/llama-embed.service`:

```ini
[Unit]
Description=llama.cpp embedding server (bge-m3)
After=network.target

[Service]
Type=simple
User=yourusername
ExecStart=/home/yourusername/llama.cpp/build/bin/llama-server \
  --model /home/yourusername/models/bge-m3-Q8_0.gguf \
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
systemctl status llama-embed
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

### Update config.py for your machine

Open `~/mcp-tools/config.py` — this is the only file you need to edit:

| Constant | Change to |
|---|---|
| `REPO_ROOT` | `/home/yourusername/repos` |
| `CHROMA_DIR` | `/home/yourusername/mcp-tools/chromadb` |
| `DOCS_ROOT` | `/home/yourusername/docs/frameworks` |
| `TOOLS_DIR` | `/home/yourusername/mcp-tools` |
| `LLM_URL` | `http://127.0.0.1:8080` (no change needed) |
| `EMBED_URL` | `http://127.0.0.1:11435/v1/embeddings` (no change needed) |

`DOCS_SOURCES` in `config.py` also contains paths — update each entry to match where you cloned the documentation libraries.

---

## 7. Index your repo

With `llama-embed` running:

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
| Model | `qwen2.5-coder-32b-instruct-q4_k_m.gguf` |
| Context window | 65536 |
| Max output tokens | 8096 |

MCP settings file — `~/.vscode-server/data/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

> **Note:** If running VS Code locally (not via Remote SSH), the path is `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

```json
{
  "mcpServers": {
    "context-engine": {
      "disabled": false,
      "timeout": 30,
      "type": "stdio",
      "command": "/home/yourusername/mcp-tools/.venv/bin/python",
      "args": ["/home/yourusername/mcp-tools/server.py"]
    },
    "docs-engine": {
      "disabled": false,
      "timeout": 30,
      "type": "stdio",
      "command": "/home/yourusername/mcp-tools/.venv/bin/python",
      "args": ["/home/yourusername/mcp-tools/docs_server.py"]
    }
  }
}
```

---

## 10. After a reboot

`llama-embed` starts automatically. Start the LLM and proxy manually:

```bash
# Terminal 1 — LLM
bash ~/start-llm.sh

# Terminal 2 — proxy
cd ~/mcp-tools && .venv/bin/python proxy.py
```

Then open VS Code. Cline will launch the MCP servers automatically.

**Startup order:** embedding server (auto) → LLM → proxy → VS Code.

> **Tip:** If performance degrades, check GPU memory usage with `nvidia-smi`. If VRAM is full, reduce the context window in Cline settings from 65536 to 32768, or switch to a smaller quantisation.

---

## Optional — start the proxy automatically on login

If you want the proxy to start automatically, create a systemd user service:

```bash
mkdir -p ~/.config/systemd/user

cat > ~/.config/systemd/user/llm-proxy.service << EOF
[Unit]
Description=LLM proxy
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/mcp-tools
ExecStart=%h/mcp-tools/.venv/bin/python %h/mcp-tools/proxy.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user enable --now llm-proxy
journalctl --user -u llm-proxy -f
```

---

## Summary of all addresses (single machine)

| Service | Address |
|---|---|
| LLM server | `http://127.0.0.1:8080` |
| Embedding server | `http://127.0.0.1:11435` |
| Proxy (Cline points here) | `http://127.0.0.1:8000` |
