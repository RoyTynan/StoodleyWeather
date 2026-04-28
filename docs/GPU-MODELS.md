# GPU Requirements and Recommended Models

You do not need 48GB of VRAM to run this setup effectively. This document explains what hardware you actually need and recommends specific coding-focused models for each GPU configuration.

---

## You Don't Need 48GB

The setup in this repo uses a 32B parameter model at Q8_0 quantisation because that hardware was available. It is not the minimum — it is the best that fits in 48GB.

A smaller model running on a 16GB or 24GB GPU, combined with the proxy's automatic context injection, can produce very good results for focused coding tasks. The proxy does a lot of the heavy lifting — the model does not need to hold the entire codebase in memory because the most relevant code is injected into every prompt automatically.

The key question is not "how big a model can I run?" but "what is the largest model that fits comfortably with room for the KV cache and OS?"

---

## What Fits in Your VRAM

Model VRAM is not the only thing to budget for. The KV cache grows with context window size and needs to fit alongside the model.

| Component | VRAM usage |
|---|---|
| Model weights | Depends on size and quantisation (see tables below) |
| KV cache (65K context, Q4_0) | ~2–4GB for a 14B model, ~4–6GB for a 32B model |
| OS and drivers | ~0.5–1GB |

**Rule of thumb:** leave at least 4–6GB free after loading the model for KV cache and OS overhead. If you reduce the context window (e.g. to 32K), the KV cache shrinks proportionally.

---

## Quantisation — Q8_0 vs Q4_K_M

| Quantisation | Size vs FP16 | Quality | Use when |
|---|---|---|---|
| Q8_0 | ~50% | Near-identical to full precision | You have the VRAM — this is the default choice |
| Q6_K | ~40% | Excellent, negligible quality loss | Tight on VRAM but want near-Q8 quality |
| Q4_K_M | ~28% | Good — some degradation on complex reasoning | Your primary option at 16–24GB |
| IQ4_XS | ~25% | Good — slightly smaller than Q4_K_M | Squeeze a larger model into limited VRAM |
| Q3_K_M | ~20% | Noticeable degradation — last resort | Only if nothing else fits |

For coding tasks, Q4_K_M is a reasonable trade-off. Code generation is more sensitive to quantisation than prose, but the quality difference between Q8_0 and Q4_K_M on a well-designed model like Qwen2.5-Coder is smaller than you might expect.

---

## Recommended Models by GPU

All model sizes below are approximate. Verify current file sizes on HuggingFace before downloading.

### 8GB VRAM
*(RTX 3070, RTX 4060 Ti 8GB, RTX 4060)*

| Model | Quantisation | Approx size | Notes |
|---|---|---|---|
| Qwen2.5-Coder-7B-Instruct | Q8_0 | ~7.2GB | Best quality that fits — strong for its size |
| Qwen2.5-Coder-7B-Instruct | Q4_K_M | ~4.1GB | Leaves headroom for larger context |

At 8GB you are limited to 7B models. Reduce context window to 32K to keep KV cache manageable.

---

### 12GB VRAM
*(RTX 3060 12GB, RTX 4070, RTX 2080 Ti)*

| Model | Quantisation | Approx size | Notes |
|---|---|---|---|
| Qwen2.5-Coder-14B-Instruct | Q4_K_M | ~8.1GB | Good quality, comfortable fit |
| Qwen2.5-Coder-14B-Instruct | Q6_K | ~10.5GB | Better quality, still fits |
| Qwen2.5-Coder-7B-Instruct | Q8_0 | ~7.2GB | Plenty of headroom |

The 14B model at Q4_K_M is the recommended choice at this tier — noticeably better than 7B for code reasoning.

---

### 16GB VRAM
*(RTX 3080, RTX 4080, RTX 4060 Ti 16GB, A4000)*

| Model | Quantisation | Approx size | Notes |
|---|---|---|---|
| Qwen2.5-Coder-14B-Instruct | Q8_0 | ~14.3GB | Near full quality — recommended |
| Qwen2.5-Coder-14B-Instruct | Q6_K | ~10.5GB | Leaves more room for KV cache |
| Codestral-22B | Q4_K_M | ~13GB | Mistral's dedicated coding model — worth trying |

16GB is a sweet spot. The 14B model at Q8_0 fits with just enough room for a 32K–65K KV cache at Q4_0. This is a very capable setup for the proxy-based workflow.

---

### 24GB VRAM
*(RTX 3090, RTX 4090, A5000, RTX 6000)*

| Model | Quantisation | Approx size | Notes |
|---|---|---|---|
| Qwen2.5-Coder-32B-Instruct | Q4_K_M | ~18.5GB | Same 32B architecture, lower quantisation than this repo's Q8_0 — recommended |
| Qwen2.5-Coder-32B-Instruct | IQ4_XS | ~16GB | Slightly smaller, similar quality to Q4_K_M |
| Qwen2.5-Coder-14B-Instruct | Q8_0 | ~14.3GB | Comfortably fits with full 65K context |
| Codestral-22B | Q8_0 | ~23GB | Tight but fits — excellent coding model |

24GB is where this setup really comes into its own. The 32B model at Q4_K_M gives you the same architecture as the full Q8_0 setup with a modest quality reduction — for most coding tasks the difference is small.

---

### 48GB VRAM
*(2× RTX 3090/4090, RTX 6000 Ada, Mac M-series 48GB, A6000)*

| Model | Quantisation | Approx size | Notes |
|---|---|---|---|
| Qwen3.6-35B-A3B | Q8_0 | ~38GB | MoE — 3B active params, fast inference, 100K context. Current model in this repo — see [LLM-QWEN3.md](LLM-QWEN3.md) |
| Qwen2.5-Coder-32B-Instruct | Q8_0 | ~34.8GB | Dense — full quality, 65K context |
| Qwen2.5-Coder-32B-Instruct | Q4_K_M | ~18.5GB | Leaves substantial headroom |

At this tier you can run large models at full Q8_0 with a 65K–100K context window and have room to spare.

---

## Apple Silicon — Unified Memory

Apple Silicon uses unified memory shared between CPU and GPU. The figures below include all processes (OS, VS Code, browser, etc.).

| Unified memory | Recommended model |
|---|---|
| 16GB | Qwen2.5-Coder-7B Q8_0 — reduce context to 32K |
| 24GB | Qwen2.5-Coder-14B Q4_K_M or Q6_K |
| 32GB | Qwen2.5-Coder-14B Q8_0, or 32B IQ4_XS (tight) |
| 48GB | Qwen2.5-Coder-32B Q4_K_M comfortably |
| 64GB | Qwen2.5-Coder-32B Q8_0 — full setup as in [SINGLE-MACHINE-MAC.md](SINGLE-MACHINE-MAC.md) |
| 96GB+ | Qwen2.5-Coder-32B Q8_0 with headroom, or larger models |

---

## Where to Download

All models are available from HuggingFace. The **bartowski** organisation maintains high-quality GGUF quantisations of most models:

- Qwen2.5-Coder series: search `bartowski/Qwen2.5-Coder-*-Instruct-GGUF`
- Codestral: search `bartowski/Codestral-*-GGUF`

Download with wget as described in [AI-SETUP.md](AI-SETUP.md#3-downloads-required), substituting the model filename.

> **Note:** The model landscape evolves quickly. New releases and quantisations appear regularly. Check HuggingFace for the latest options — a newer 14B model may outperform an older 32B on coding benchmarks.

---

## No GPU — CPU-Only with Conventional RAM

If you do not have a discrete GPU, llama.cpp can run entirely on CPU using system RAM. Performance is significantly slower — expect 2–8 tokens per second depending on your CPU and model size — but for a proxy-assisted workflow where Cline submits one focused task at a time, this is often acceptable. You are not waiting for interactive streaming; you submit a prompt and come back.

The key difference from VRAM is that RAM is cheap and plentiful. A machine with 32GB or 64GB of RAM can run models that no consumer GPU can fit.

### Recommended models for CPU-only use

Prioritise **small, well-quantised models** that generate tokens quickly rather than large models that fit but crawl. Q4_K_M is the right default — it gives a good quality-to-size ratio and keeps generation fast.

| Model | Quantisation | Approx size | Min RAM | Notes |
|---|---|---|---|---|
| Qwen2.5-Coder-7B-Instruct | Q4_K_M | ~4.1GB | 8GB | Fast on CPU — good first choice |
| Qwen2.5-Coder-7B-Instruct | Q8_0 | ~7.2GB | 12GB | Near-full quality, still manageable |
| Qwen2.5-Coder-14B-Instruct | Q4_K_M | ~8.1GB | 16GB | Noticeably better reasoning than 7B |
| Qwen2.5-Coder-14B-Instruct | Q6_K | ~10.5GB | 16GB | Better quality, still CPU-viable |
| Phi-4-mini-instruct | Q4_K_M | ~2.5GB | 6GB | Microsoft's 3.8B model — punches above its size |
| SmolLM2-1.7B-Instruct | Q8_0 | ~1.8GB | 4GB | Extremely fast, limited reasoning — for simple edits only |

### CPU performance tips

**Use `-ngl 0` in llama.cpp** to disable GPU offloading entirely — this avoids llama.cpp attempting partial GPU offload and failing silently on machines without compatible drivers.

**Reduce threads to match physical cores, not logical.** Hyperthreading does not help LLM inference. Set `-t` to the number of physical cores. On a 6-core/12-thread CPU, use `-t 6`.

**Reduce context window to 16K or 32K.** The KV cache lives in RAM on CPU runs and grows linearly with context size. A 65K context on a 14B model can consume 8–12GB of RAM on top of the model weights. Reduce `--ctx-size` in `start-llm.sh` if RAM is tight.

**Use `--mmap` (enabled by default in llama.cpp).** Memory-mapped model loading means the OS can page model weights in and out. On machines with enough RAM to hold the full model this makes no difference, but on tighter setups it prevents out-of-memory crashes at the cost of slightly slower first-token latency.

### Example `start-llm.sh` flags for CPU-only

```bash
./llama-server \
  --model models/qwen2.5-coder-7b-instruct-q4_k_m.gguf \
  --ctx-size 32768 \
  --threads 6 \
  --ngl 0 \
  --host 0.0.0.0 \
  --port 8080
```

### Does the proxy still work?

Yes — identically. llama.cpp's `/v1/chat/completions` endpoint is the same whether the model runs on GPU or CPU. The proxy, MCP server, ChromaDB enrichment, and Cline integration are all unaffected. The only thing that changes is generation speed.

For the hybrid workflow (Gemini → Claude Code → Cline), slower generation is less of a problem than it sounds. Cline submits one focused, proxy-enriched prompt at a time. A 7B model generating at 5 tok/s will complete a typical code edit in 30–60 seconds — slow compared to a GPU, but not a blocker for a workflow that already involves human review between every step.

---

## Does a Smaller Model Change the Setup?

No. The proxy, MCP server, clinerules, and workflow are identical regardless of which model you run. The only changes are:

- The model filename in `start-llm.sh`
- The model name in Cline's provider settings
- Possibly the context window size if VRAM is tight

Everything else — ChromaDB, the file watcher, the hybrid Claude Code workflow — works exactly the same.
