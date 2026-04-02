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
| Qwen2.5-Coder-32B-Instruct | Q8_0 | ~34.8GB | Full quality — this is what this repo uses |
| Qwen2.5-Coder-32B-Instruct | Q4_K_M | ~18.5GB | Leaves substantial headroom |

At this tier you can run the 32B model at full Q8_0 with a 65K context window and have room to spare. This is the configuration documented in [AI-SETUP.md](AI-SETUP.md).

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

## Does a Smaller Model Change the Setup?

No. The proxy, MCP server, clinerules, and workflow are identical regardless of which model you run. The only changes are:

- The model filename in `start-llm.sh`
- The model name in Cline's provider settings
- Possibly the context window size if VRAM is tight

Everything else — ChromaDB, the file watcher, the hybrid Claude Code workflow — works exactly the same.
