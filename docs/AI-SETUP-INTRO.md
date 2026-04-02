# AI Setup — Introduction

This is a summary of the full setup described in [AI-SETUP.md](AI-SETUP.md).

---

## What this is

A three-machine home LAN setup for AI-assisted software development using a locally-hosted large language model — no cloud API, no subscription, no data leaving the house.

```
Mac mini  →  i7 Ubuntu  →  i9 Ubuntu
(VS Code)    (proxy, MCP,    (LLM inference)
              embeddings)
```

---

## The machines

| Machine | Role | Key hardware |
|---|---|---|
| Mac mini | Thin client — VS Code only | — |
| i7 Ubuntu | Development machine, proxy, embeddings | RTX 2060 (6GB VRAM) |
| i9 Ubuntu | LLM inference | RTX 3090 + Blackwell PRO 4000 = 48GB VRAM |

You do not need two Ubuntu machines or 48GB of VRAM — 24GB in a single machine will work. This documents what was used here.

---

## The model

**Qwen2.5-Coder-32B-Instruct-Q8_0** running via llama.cpp on the i9.

- 32.7B parameters, Q8_0 quantisation (34.8GB)
- Runs fully in GPU VRAM across both i9 GPUs
- 65,536 token context window
- Exposes an OpenAI-compatible API on port 8080

---

## The workflow

- **Cline + local LLM** — executing specific coding tasks

Cline executes prompts against the local LLM.

---

## The proxy

A FastAPI server (`proxy.py`) runs on the i7 between Cline and the LLM. Every request Cline sends is intercepted. The proxy:

1. Detects which repo is being worked on from the conversation history
2. Runs a **hybrid search** to find the most relevant code chunks from that repo
3. Injects them into the prompt before forwarding to the i9

**Hybrid search** combines two methods and merges the results using Reciprocal Rank Fusion (RRF):

- **Vector search** — embeds the prompt and queries ChromaDB for semantically similar chunks
- **BM25 keyword search** — scores all chunks using TF-IDF-style keyword matching against an in-memory index built at startup

Using both methods together is more reliable than either alone — vector search finds conceptually related code, BM25 finds exact function names and identifiers.

This gives the local LLM relevant codebase context on every request automatically.

**Exception:** if the prompt contains a file path (`src/`), enrichment is skipped — Cline reads the file directly via the MCP server instead, which is more reliable for edit tasks.

The proxy also runs a file watcher. When a file is saved in VS Code, the relevant repo is re-indexed into ChromaDB after a 3-second debounce — so the context is always current.

---

## The MCP server

`server.py` is a FastMCP server that Cline connects to for direct file access. The key tool Cline uses is `read_repo_file` — it reads a specific file from the repo before making an edit, giving the model clean, accurate file content.

---

## ChromaDB

An open-source Python vector database that stores embeddings of all source files. Lives at `/mnt/storage/chromadb/` on the i7. Built and kept up to date by `index_repos.py`, which runs automatically on file save (via the proxy watcher) and on git commit (via a post-commit hook).

---

## Embeddings

`nomic-embed-text-v1.5` runs as a systemd service (`llama-embed`) on the i7's RTX 2060. Used by:
- `index_repos.py` — to embed source file chunks when indexing
- `proxy.py` — to embed incoming prompts before querying ChromaDB

---

## Cline configuration

| Setting | Value |
|---|---|
| API Provider | OpenAI Compatible |
| Base URL | `http://<i7-ip>:8000/v1` (the proxy — not the i9 directly) |
| Context window | 65,536 |
| Native Tool Call | Off |
| Parallel Tool Calling | Off |

---

## Clinerules

A set of rules in `.clinerules/` that constrain Cline's behaviour with the local LLM:

- No editing files unless the user explicitly uses "edit", "change", "fix", or "update"
- No running terminal commands or the dev server unless explicitly asked
- When appending to a file, always read it first and use the last line as the edit anchor — never rewrite the whole file
- Never delete or rename anything without explicit instruction
- Short responses only — one confirmation line after completing a task

These rules exist because local LLMs are more prone to overreach than cloud models. The rules keep Cline focused on the specific task given.

---

## After a reboot

1. SSH to i9 → `bash start-llm.sh`
2. On i7 → `cd /mnt/storage/mcp-tools && .venv/bin/python proxy.py`
3. Open VS Code — Cline launches the MCP servers automatically

---

For full setup instructions, hardware details, and all configuration options, see [AI-SETUP.md](AI-SETUP.md).
