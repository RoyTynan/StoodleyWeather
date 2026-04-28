# Qwen3.6-35B-A3B — Setup and Configuration

I updated to this LLM on Tuesday 28th April 2026


Qwen3.6-35B-A3B is a Mixture of Experts (MoE) model with 35B total parameters and 3B active parameters per forward pass. It is significantly faster than the previous dense Qwen2.5-Coder-32B at inference time, with comparable or better code quality.

---

## Download

```bash
wget --header="Authorization: Bearer your-huggingface-token" \
    https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF/resolve/main/Qwen3.6-35B-A3B-Q8_0.gguf \
    -O /home/roy/models/Qwen3.6-35B-A3B-Q8_0.gguf \
    --continue --progress=dot:giga
```

`--continue` allows resuming an interrupted download.

---

## Start Script

```bash
pkill llama-server
sleep 2

SERVER_BIN="/home/roy/llama.cpp/build/bin/llama-server"
MODEL_PATH="/home/roy/models/Qwen3.6-35B-A3B-Q8_0.gguf"

$SERVER_BIN \
  -m "$MODEL_PATH" \
  --host 0.0.0.0 \
  --port 8080 \
  -ngl 99 \
  -fa on \
  --no-mmap \
  -c 102400 \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --split-mode layer \
  --tensor-split 1,1 \
  -b 4096 \
  -ub 4096
```

**Key flags:**

| Flag | Value | Purpose |
|---|---|---|
| `-ngl 99` | — | Offload all layers to GPU |
| `-fa on` | — | Flash attention — faster, less VRAM |
| `--no-mmap` | — | Required for multi-GPU splits |
| `-c` | `102400` | 100K context window (up from 65K on previous model) |
| `--cache-type-k/v` | `q8_0` | Higher quality KV cache — affordable because MoE has fewer attention layers (~28 vs 64 on dense models) |
| `--split-mode` | `layer` | Split model layers across GPUs |
| `--tensor-split` | `1,1` | Equal split between RTX 3090 and Blackwell PRO 4000 |
| `-b / -ub` | `4096` | Batch size — faster prefill |

---

## VRAM Usage

On the i9 (RTX 3090 24GB + Blackwell PRO 4000 24GB = 48GB total):

| | GPU 0 (RTX 3090) | GPU 1 (Blackwell) | Total |
|---|---|---|---|
| In use | ~22 GB | ~22 GB | ~44 GB |
| Free | ~2.5 GB | ~2.5 GB | ~5 GB |

The MoE architecture means the KV cache is much smaller than on an equivalent dense model — freeing headroom for q8_0 cache quality and 100K context simultaneously.

---

## Proxy Configuration

Qwen3 outputs `<think>...</think>` reasoning blocks before tool calls. Cline cannot parse these. Set the following in `config.py` on the i7:

```python
LLM_HAS_THINKING = True
```

The proxy will suppress thinking blocks at the model level (`enable_thinking: false` in every request) and strip any that leak through before returning to Cline.

When switching back to a non-thinking model (Qwen2.5, Llama, etc.), set `LLM_HAS_THINKING = False` and restart the proxy.

---

## Cline Settings

| Setting | Value |
|---|---|
| Context window | `102400` |
| Max output tokens | `8096` |
| Model | `Qwen3.6-35B-A3B-Q8_0.gguf` |
