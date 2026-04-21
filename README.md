# StoodleyWeather

A simple Next.js weather app for Stoodley Pike, near Todmorden in West Yorkshire.

# Just to clarify any confusion

This repo is about setting up and configuring an LLM (Large Language Model) locally on a home network or a single machine.

The whole point of this repo is described via the documents found at the bottom of this page.

It is about setting up and running llama server, specifically llama.cpp, to act as a software coding assistant along the lines of Claude Code.

The app that's presented and gives the name to the repo, StoodleyWeather, is a test Next.js app that allows a user to test the coding assistant against a real-world application.<br>


# What this "system" does

An i7 Ubuntu machine runs an embedding server (bge-m3-Q8_0 via llama.cpp) and a FastAPI proxy, while an i9 Ubuntu machine with 48GB VRAM runs the main LLM (Qwen2.5-Coder-32B). 

At its core is a RAG (Retrieval-Augmented Generation) pipeline — source code from all active repos is chunked and embedded into 1024-dimensional vectors, then persisted in ChromaDB, a local vector database that stores both the embeddings and the original source chunks with metadata (file path, line numbers, repo name). 

At query time ChromaDB performs approximate nearest-neighbour search to find semantically similar chunks, which are combined with BM25 keyword results and fused through Reciprocal Rank Fusion. 

This candidate pool is then passed through a cross-encoder reranker (ms-marco-MiniLM-L-6-v2) which scores each chunk against the actual query as a pair rather than independently — producing a much more precise final selection than vector similarity alone can achieve. 

The enriched context is injected into every prompt sent to the LLM, meaning Cline receives highly accurate codebase context without you having to manually reference files. 

The system also exposes its capabilities — semantic search, file reading, documentation search, and automated build/type verification — as MCP (Model Context Protocol) tools, allowing Claude Code and Cline to call them directly as part of their agentic workflows. 

Repos are watched for file changes and re-indexed automatically, per-repo .chromaignore files exclude large data files from the index, and the whole stack is documented with a new-project checklist so it can be extended quickly.

The Python code to run all of this is presented in this repo.

Everything is documented, see the documents given at the bottom of this page.

# Introduction

Hello, my name is Roy Tynan. I live in West Yorkshire, England. I'm an electronics engineer / software engineer with quite a number of years ( too many ) development experience.

During March 2026 I decided to set up my own LLM (large language model) system. I was fortunate enough to already have two Ubuntu machines — one with a NVIDIA RTX 2060 GPU and the other with a NVIDIA RTX 3090. I experimented with running smaller LLMs and tried to split the LLM across the two machines, but it proved very difficult and was very unstable.

So I purchased an NVIDIA Blackwell RTX PRO 4000 GPU card and placed it alongside the RTX 3090, giving me a total of 48GB of GPU VRAM in one machine. This worked really well and I was quite pleased with the results. By results I mean something like a Claude Code style of coding assistant but running entirely locally.

I was also conscious that I was under using my other Ubuntu machine — the one with the RTX 2060 — so I brought that into the setup as well, using it to run semantic search and embeddings.

Hopefully this repo and the document you are currently reading will help you set up a modern LLM system for yourself. You do not need two Ubuntu machines, and you do not need 48GB of GPU VRAM — 24GB in a single machine will work. But this document explains how I did it for my setup.

I hope this helps. Thank you, and regards — Roy.

If you find it useful and you're a GitHub member, a GitHub star is always appreciated —
it helps others find it.


## Contact

You can contact me on roytynandev@gmail.com<br><br>
I try to reply to everyone but I can't guarantee a quick response.<br>
Any criticisms please keep constructive, otherwise I'll just crawl off to my local pub for a calming beer or ten.


## Purpose

This app was created as a test project for a **AI-assisted development workflow**:

- **Cline + local LLM** — executing specific coding tasks against Qwen2.5-Coder-32B running entirely on local hardware via llama.cpp

The workflow uses a **FastAPI proxy** on the development machine that intercepts every Cline request and automatically enriches it with relevant code context from a ChromaDB vector database — so the local LLM always has the most relevant parts of the codebase in its context window without needing to be told explicitly.

The actual subject of the experiment is the development workflow itself: the proxy, MCP tools for file access, clinerules to guide model behaviour, and the combination of a reasoning model (Claude Code) with a local execution model (Cline + Qwen).

See the documentation links for the AI setup at the bottom of this readme.

## What this Next.js app does

- Fetches hourly weather data for Stoodley Pike from the [Open-Meteo](https://open-meteo.com) free API
- Stores the data locally in the browser's IndexedDB
- Displays hourly breakdowns for rain, surface pressure, wind (direction, speed, gusts), and visibility
- Shows a temperature heatmap across all hours
- Shows a summit conditions indicator (go/no-go score per hour based on wind, visibility, precipitation, temperature)
- Shows a grid of sparkline charts for all key metrics

## Getting Started

```bash
git clone <repo>
cd stoodley-weather
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

No API keys or environment variables are required. The app uses the Open-Meteo free tier which is open access.

## Tech Stack for this test project

- [Next.js 16](https://nextjs.org) — React framework
- [Tailwind CSS v4](https://tailwindcss.com) — styling
- [Open-Meteo API](https://open-meteo.com) — weather data
- Browser IndexedDB — local data storage
- SVG — charts rendered without any chart library


## This test project structure

```
src/
├── api/
│   └── weather.ts                # Open-Meteo fetch and data transformation
├── app/
│   ├── api/weather/route.ts      # Next.js API route
│   ├── main-content.tsx          # Main page orchestration
│   ├── compass.tsx               # Wind direction compass component
│   ├── header.tsx
│   └── page.tsx
├── components/
│   ├── SparkLine.tsx             # SVG sparkline chart component
│   ├── WeatherTable.tsx          # Hourly data table component
│   ├── TemperatureHeatmap.tsx    # 24-hour temperature heatmap
│   └── SummitConditions.tsx      # Per-hour summit go/no-go indicator
├── lib/
│   ├── constants.ts              # Shared constants (coordinates)
│   ├── weather-db.ts             # IndexedDB read/write
│   └── weather-utils.ts          # Utility functions (Beaufort, compass, visibility, summit score)
└── types/
    └── types.ts                  # TypeScript interfaces
```

## Documentation for the AI setup

| File | Description |
|---|---|
| [docs/NEW-PROJECT.md](docs/NEW-PROJECT.md) | Step-by-step checklist for adding a new project — clinerules, indexing, verification |
| [docs/AI-SETUP-INTRO.md](docs/AI-SETUP-INTRO.md) | Quick summary of the AI setup — workflow, proxy, ChromaDB, and Cline configuration |
| [docs/AI-SETUP.md](docs/AI-SETUP.md) | Full walkthrough of the local LLM hardware setup, MCP servers, ChromaDB indexing, and Cline configuration |
| [docs/HYBRID-WORKFLOW.md](docs/HYBRID-WORKFLOW.md) | How to use Claude Code for reasoning and planning, and Cline for execution |
| [docs/GPU-MODELS.md](docs/GPU-MODELS.md) | Recommended coding models for each GPU tier — 8GB to 48GB |
| [docs/SINGLE-MACHINE-MAC.md](docs/SINGLE-MACHINE-MAC.md) | How to run the full setup on a single Apple Silicon Mac (64GB+ unified memory) |
| [docs/SINGLE-MACHINE-WINDOWS.md](docs/SINGLE-MACHINE-WINDOWS.md) | How to run the full setup on a single Windows machine with an NVIDIA GPU |
| [docs/SINGLE-MACHINE-LINUX.md](docs/SINGLE-MACHINE-LINUX.md) | How to run the full setup on a single Linux machine with an NVIDIA GPU |
| [docs/ADDING-DOCS.md](docs/ADDING-DOCS.md) | How to add documentation libraries (React, TypeScript, Next.js) to the RAG system |
| [docs/CLINE-PROMPTS.md](docs/CLINE-PROMPTS.md) | Example prompts for using Cline with the MCP tools — semantic search, doc search, code tasks |
| [_python-files/](_python-files/) | The MCP server, proxy and indexer Python scripts ready to copy to your own machine |
| [docs/MAC-XCODE-ISSUES.md](docs/MAC-XCODE-ISSUES.md) | Running the proxy and MCP tools on a Mac when Xcode or other Mac-only tooling is required |
