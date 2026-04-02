# Single Machine Setup — Windows (NVIDIA GPU)

This document covers how to run the full AI development setup described in [AI-SETUP.md](AI-SETUP.md) on a single Windows machine with an NVIDIA GPU and at least 16GB of VRAM.

No second machine is needed. The LLM, embedding server, proxy, and MCP servers all run on the same machine.

> **Heat warning:** Running a large language model under sustained load will push your GPU to high temperatures. On a desktop this is manageable with good case airflow. On a gaming laptop the fans will run continuously and thermal throttling may reduce performance — keep it plugged in and on a hard surface.

---

## Prerequisites

- Windows 10 or 11
- NVIDIA GPU with CUDA support (GTX 10 series or newer)
- NVIDIA drivers installed and up to date
- At least 16GB VRAM — see [GPU-MODELS.md](GPU-MODELS.md) for model recommendations by VRAM size

---

## Differences from the multi-machine Linux setup

| Aspect | Multi-machine Linux | Single Windows |
|---|---|---|
| LLM backend | CUDA | CUDA |
| Machines | 3 | 1 |
| GPU split | `--split-mode layer` across 2 GPUs | Not needed |
| Network addresses | LAN IPs | `127.0.0.1` / `localhost` throughout |
| Systemd services | Yes | Not available — manual startup or Task Scheduler |
| llama.cpp build | CMake on Linux | CMake on Windows (Visual Studio required) |
| Shell | bash | PowerShell or Command Prompt |
| Python venv activation | `.venv/bin/python` | `.venv\Scripts\python.exe` |

---

## 1. Install prerequisites

### CUDA Toolkit

Download and install from NVIDIA: https://developer.nvidia.com/cuda-downloads

Verify with:
```powershell
nvcc --version
nvidia-smi
```

### Build tools

Install **Visual Studio 2022** (Community edition is free) with the **Desktop development with C++** workload. This provides the compiler and CMake that llama.cpp requires.

Download from: https://visualstudio.microsoft.com/downloads/

### Git

Download from: https://git-scm.com/download/win

### Python and uv

Install Python 3.13 from: https://www.python.org/downloads/

Then install uv:
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### ripgrep

```powershell
winget install BurntSushi.ripgrep.MSVC
```

---

## 2. Build llama.cpp with CUDA

Open the **Developer PowerShell for VS 2022** (search for it in the Start menu — this sets up the compiler environment):

```powershell
git clone https://github.com/ggerganov/llama.cpp.git C:\llama.cpp
cd C:\llama.cpp
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release -j $env:NUMBER_OF_PROCESSORS
```

The built binaries will be in `C:\llama.cpp\build\bin\Release\`.

---

## 3. Download the models

### LLM

```powershell
mkdir C:\models
curl -L -H "Authorization: Bearer your-huggingface-token" `
    -o C:\models\Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf `
    "https://huggingface.co/bartowski/Qwen2.5-Coder-32B-Instruct-GGUF/resolve/main/Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf"
```

> **Note:** On Windows, 24GB VRAM is the practical maximum for a single consumer GPU. The Q4_K_M quantisation (~18.5GB) fits comfortably. See [GPU-MODELS.md](GPU-MODELS.md) for the right model for your VRAM.

### Embedding model

```powershell
python -c "
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id='nomic-ai/nomic-embed-text-v1.5-GGUF',
    filename='nomic-embed-text-v1.5.Q4_K_M.gguf',
    local_dir='C:/models/'
)"
```

---

## 4. Create the startup scripts

### LLM server

Create `C:\llama\start-llm.bat`:

```bat
@echo off
taskkill /IM llama-server.exe /F 2>nul
timeout /t 2 /nobreak >nul

set SERVER_BIN=C:\llama.cpp\build\bin\Release\llama-server.exe
set MODEL_PATH=C:\models\Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf

%SERVER_BIN% ^
  -m %MODEL_PATH% ^
  --host 127.0.0.1 ^
  --port 8080 ^
  -ngl 99 ^
  -fa on ^
  --no-mmap ^
  -c 65536 ^
  --cache-type-k q4_0 ^
  --cache-type-v q4_0 ^
  -b 2048 ^
  -ub 2048
```

### Embedding server

Create `C:\llama\start-embed.bat`:

```bat
@echo off
set SERVER_BIN=C:\llama.cpp\build\bin\Release\llama-server.exe
set MODEL_PATH=C:\models\nomic-embed-text-v1.5.Q4_K_M.gguf

%SERVER_BIN% ^
  --model %MODEL_PATH% ^
  --port 11435 ^
  --host 127.0.0.1 ^
  --ctx-size 8192 ^
  --batch-size 2048 ^
  --embedding ^
  --pooling mean ^
  --gpu-layers 99 ^
  --log-disable
```

Run each script by double-clicking or from PowerShell:

```powershell
Start-Process "C:\llama\start-embed.bat"
Start-Process "C:\llama\start-llm.bat"
```

> **Note on `-b` / `-ub`:** Start at 2048. If you have VRAM to spare, increase to 4096 for faster prompt processing.

---

## 5. Set up the MCP tools

```powershell
mkdir C:\mcp-tools
Copy-Item -Path \path\to\repo\_python-files\* -Destination C:\mcp-tools -Recurse
cd C:\mcp-tools
uv sync
```

### Update config.py for Windows

Open `C:\mcp-tools\config.py` and update the following — this is the only file you need to edit:

| Constant | Change to |
|---|---|
| `REPO_ROOT` | `C:/Users/yourusername/repos` |
| `CHROMA_DIR` | `C:/mcp-tools/chromadb` |
| `DOCS_ROOT` | `C:/docs/frameworks` |
| `TOOLS_DIR` | `C:/mcp-tools` |
| `LLM_URL` | `http://127.0.0.1:8080` (no change needed) |
| `EMBED_URL` | `http://127.0.0.1:11435/v1/embeddings` (no change needed) |

> **Use forward slashes in Python paths** — `C:/Users/...` not `C:\Users\...`. Python handles forward slashes correctly on Windows and avoids escape sequence issues.

`DOCS_SOURCES` in `config.py` also contains paths — update each entry to match where you cloned the documentation libraries.

---

## 6. Index your repo

With the embedding server running:

```powershell
cd C:\mcp-tools
.venv\Scripts\python.exe index_repos.py --repo yourreponame
```

---

## 7. Install the git post-commit hook

In each repo:

```powershell
$hook = ".git\hooks\post-commit"
@"
#!/bin/sh
echo "[post-commit] re-indexing..."
C:/mcp-tools/.venv/Scripts/python.exe C:/mcp-tools/index_repos.py --repo yourreponame &
"@ | Set-Content $hook
```

---

## 8. Configure Cline

In VS Code, configure the Cline provider:

| Setting | Value |
|---|---|
| API Provider | OpenAI Compatible |
| Base URL | `http://127.0.0.1:8000/v1` |
| API Key | `local` |
| Model | `qwen2.5-coder-32b-instruct-q4_k_m.gguf` |
| Context window | 65536 |
| Max output tokens | 8096 |

MCP settings file — `%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`:

```json
{
  "mcpServers": {
    "context-engine": {
      "disabled": false,
      "timeout": 30,
      "type": "stdio",
      "command": "C:\\mcp-tools\\.venv\\Scripts\\python.exe",
      "args": ["C:\\mcp-tools\\server.py"]
    },
    "docs-engine": {
      "disabled": false,
      "timeout": 30,
      "type": "stdio",
      "command": "C:\\mcp-tools\\.venv\\Scripts\\python.exe",
      "args": ["C:\\mcp-tools\\docs_server.py"]
    }
  }
}
```

> **Note:** The MCP settings JSON requires backslashes to be escaped (`\\`). The `config.py` file uses forward slashes — these are different contexts.

---

## 9. Start the proxy

```powershell
cd C:\mcp-tools
.venv\Scripts\python.exe proxy.py
```

Leave this running in a terminal window. The proxy logs all requests, injected chunks, and file watcher events here.

---

## 10. After a reboot

Open three PowerShell windows in order:

```powershell
# Window 1 — embedding server
C:\llama\start-embed.bat

# Window 2 — LLM
C:\llama\start-llm.bat

# Window 3 — proxy
cd C:\mcp-tools && .venv\Scripts\python.exe proxy.py
```

Then open VS Code. Cline will launch the MCP servers automatically.

> **Tip:** If the system becomes sluggish, open Task Manager → Performance → GPU and check GPU Memory. If usage is near 100%, reduce the context window in Cline settings from 65536 to 32768, or switch to a smaller quantisation.

---

## Windows Firewall

The LLM server, embedding server, and proxy all bind to `127.0.0.1` (localhost only). Windows Firewall will not block localhost traffic, so no firewall rules are needed.

If you want to access the LLM from another machine on your network, change `--host 127.0.0.1` to `--host 0.0.0.0` in the startup script and allow the port through Windows Firewall — but this is not required for the single-machine setup.

---

## Summary of all addresses (single machine)

| Service | Address |
|---|---|
| LLM server | `http://127.0.0.1:8080` |
| Embedding server | `http://127.0.0.1:11435` |
| Proxy (Cline points here) | `http://127.0.0.1:8000` |
