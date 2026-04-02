# StoodleyWeather

A simple Next.js weather app for Stoodley Pike, near Todmorden in West Yorkshire.


Hello, my name is Roy Tynan. I live in West Yorkshire, England. I'm an electronics engineer / software engineer with quite a number of years ( too many ) development experience.

During March 2026 I decided to set up my own LLM (large language model) system. I was fortunate enough to already have two Ubuntu machines — one with a NVIDIA RTX 2060 GPU and the other with a NVIDIA RTX 3090. I experimented with running smaller LLMs and tried to split the LLM across the two machines, but it proved very difficult and was very unstable.

So I purchased an NVIDIA Blackwell RTX PRO 4000 GPU card and placed it alongside the RTX 3090, giving me a total of 48GB of GPU VRAM in one machine. This worked really well and I was quite pleased with the results. By results I mean something like a Claude Code style of coding assistant but running entirely locally.

I was also conscious that I was under using my other Ubuntu machine — the one with the RTX 2060 — so I brought that into the setup as well, using it to run semantic search and embeddings.

Hopefully this repo and the document you are currently reading will help you set up a modern LLM system for yourself. You do not need two Ubuntu machines, and you do not need 48GB of GPU VRAM — 24GB in a single machine will work. But this document explains how I did it for my setup.

I hope this helps. Thank you, and regards — Roy.

This repository and everything in it is shared freely and publicly on GitHub. No paywalls, no
newsletter signups, no courses to buy. If it saves you time or helps you get your own setup
running, that is reward enough. 
If you find it useful and you're a GitHub member, a GitHub star is always appreciated —
it helps others find it.


## Contact

You can contact me on roytynandev@gmail.com<br><br>
I try to reply to everyone but I can't guarantee a quick response.<br>
Any criticisms please keep constructive, otherwise I'll just crawl off to my local pub for a calming beer or 10.


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
