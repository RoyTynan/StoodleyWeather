# StoodleyWeather AI Development Setup

A home LAN or single computer setup for AI-assisted software development using a locally-hosted LLM — no cloud API, no subscription, no data leaving the house.

```
Mac mini  →  i7 Ubuntu  →  i9 Ubuntu
(VS Code)    (proxy, MCP,    (LLM inference)
              embeddings,
              monitor)
```

Cline in VS Code sends every prompt through a proxy on the i7. The proxy enriches it with relevant code from ChromaDB before forwarding to the LLM on the i9. The LLM never sees the whole codebase — only the parts that matter for the current task.

---

## Introduction

Hello, my name is Roy Tynan. I live in West Yorkshire, England. I'm an electronics engineer / software engineer with quite a number of years (too many) development experience.

During early March 2026 I decided to set up my own LLM system. I was fortunate enough to already have two Ubuntu machines — one with an NVIDIA RTX 2060 GPU and the other with an NVIDIA RTX 3090. I experimented with running smaller LLMs and tried to split the LLM across the two machines, but it proved very difficult and was very unstable.

So I purchased an NVIDIA Blackwell RTX PRO 4000 GPU card and placed it alongside the RTX 3090, giving me a total of 48GB of GPU VRAM in one machine. This worked really well. By results I mean something like a Claude Code style of coding assistant but running entirely locally.

You do not need two Ubuntu machines, and you do not need 48GB of GPU VRAM — 24GB in a single machine will work. But this document explains how I did it for my setup.

I hope this helps. Thank you, and regards — Roy.

If you find it useful and you're a GitHub member, a GitHub star is always appreciated — it helps others find it.

**Contact:** roytynandev  gmail.com     

don't forget the @ before gmail

---

## Update

On May 9th 2026 I migrated this setup by port-forwarding the Ubuntu machine  (RTX2060) known as i7 which hosts this RAG. It's available over the internet to another member of the current development team I work with; it's a Cloudflare, Python and  React.native app.


## What the System Does

### "It's not just about the size of the LLM, it's also so important to get the right infrastructure in place around the LLM"

At its core is a RAG (Retrieval-Augmented Generation) pipeline — source code from all active repos is chunked and embedded into 1024-dimensional vectors, then persisted in ChromaDB, a local vector database. At query time ChromaDB performs approximate nearest-neighbour search to find semantically similar chunks, which are combined with BM25 keyword results and fused through Reciprocal Rank Fusion. This candidate pool is then passed through a cross-encoder reranker which scores each chunk against the actual query as a pair — producing a much more precise final selection than vector similarity alone.

The enriched context is injected into every prompt sent to the LLM, meaning Cline receives highly accurate codebase context without you having to manually reference files.

The system also exposes its capabilities as MCP (Model Context Protocol) tools, allowing Claude Code and Cline to call semantic search, file reading, documentation search, and automated build/type verification directly as part of their agentic workflows.

Repos are watched for file changes and re-indexed automatically. Per-repo `.chromaignore` files exclude large data files from the index. A prompt monitor provides a full audit trail of every LLM interaction — what was injected, what was sent, what was returned, and token counts per step.

Context compaction runs automatically in two layers. **Layer 1** runs on every request without any LLM call — the proxy strips fenced code blocks and large tool-result bodies from messages older than the last four. **Layer 2** runs in the background when the prompt token count crosses a configurable threshold: the proxy sends old messages one at a time to the LLM for summarisation and swaps the summaries in on subsequent requests. When a HALT (context saturation) fires, the proxy runs a synchronous compaction pass and retries the request once before giving up — so most tasks recover transparently. A `compact_context` MCP tool is available to report current compaction savings on demand.

---

## The Test App — StoodleyWeather

This repo uses a simple Next.js weather app for Stoodley Pike, near Todmorden in West Yorkshire, as the test project for the AI workflow. The app itself is the subject of the Cline coding tasks used to validate the setup.

- Fetches hourly weather data from the [Open-Meteo](https://open-meteo.com) free API
- Stores data locally in IndexedDB
- Displays rain, pressure, wind, visibility, temperature heatmap, summit go/no-go score, and sparkline charts

```bash
npm install && npm run dev
# opens at http://localhost:3000 — no API keys required
```

---

## Documentation

| Doc | What it covers |
|---|---|
| [SETUP.md](docs/SETUP.md) | Install guide — machines, models, services, first run |
| [LLM-QWEN3.md](docs/LLM-QWEN3.md) | Qwen3.6-35B-A3B setup — download, start script, VRAM, proxy config |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | How the system works — proxy, RAG, ChromaDB, MCP, file watching |
| [MONITOR.md](docs/MONITOR.md) | LLM prompt monitor — task audit trail, step types, HALT detection |
| [WORKFLOW.md](docs/WORKFLOW.md) | Working with Cline — prompt writing, RAG vs read_file, examples |
| [GPU-MODELS.md](docs/GPU-MODELS.md) | GPU requirements and recommended models by VRAM |
| [NEW-PROJECT.md](docs/NEW-PROJECT.md) | Adding a new project to the setup |
| [ADDING-DOCS.md](docs/ADDING-DOCS.md) | Indexing framework documentation into ChromaDB |
| [MAC-XCODE-ISSUES.md](docs/MAC-XCODE-ISSUES.md) | Mac-specific notes and file sync |
| [SINGLE-MACHINE-LINUX.md](docs/SINGLE-MACHINE-LINUX.md) | Running everything on one Linux machine |
| [SINGLE-MACHINE-MAC.md](docs/SINGLE-MACHINE-MAC.md) | Running everything on one Mac |
| [SINGLE-MACHINE-WINDOWS.md](docs/SINGLE-MACHINE-WINDOWS.md) | Running everything on one Windows machine |

---


