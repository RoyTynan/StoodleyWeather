# Starting a New Project

A step-by-step checklist for adding a new project to the AI setup. Once done the proxy, ChromaDB indexing, MCP tools, and `verify_project` all work automatically — no further configuration needed for each new project.

---

## Checklist

### 1. Create or clone your repo under `REPO_ROOT`

The proxy watches everything under `REPO_ROOT` and picks up new repos automatically. Just put the project there.

```bash
cd /home/yourname/mcp-context/repos

# Clone an existing repo
git clone <your-repo-url> my-project

# Or create a new one
mkdir my-project && cd my-project && git init
```

Verify it is in the right place:

```bash
ls /home/yourname/mcp-context/repos
# my-project should appear in the list
```

---

### 2. Copy in the clinerules file

The clinerules file tells Cline how to behave — coding style, naming conventions, what not to do. Without it the local LLM has no guardrails.

Copy the clinerules from this repo as a starting point:

```bash
cp -r /home/yourname/mcp-context/repos/stoodleyweather/.clinerules my-project/.clinerules
```

Then edit `.clinerules/.clinerules.md` to match your project's language, framework, and conventions. Key things to review:

- **Language & Types** — remove TypeScript rules if your project is C++ or plain JS
- **Components** — remove React/Next.js rules if not applicable
- **Styling** — remove Tailwind rules if your project uses something else
- **Naming** — adjust to match your project's conventions
- **Git** — keep the "ask before committing" rule unless you want Cline to commit automatically

---

### 3. Trigger the initial index

The proxy file watcher will pick up file changes automatically after startup, but on a brand new project the ChromaDB index needs to be built for the first time. Either:

**Option A — trigger via the proxy API:**
```bash
curl -X POST "http://localhost:8000/reindex?repo=my-project"
```

**Option B — run the indexer directly:**
```bash
cd /mnt/storage/mcp-tools
.venv/bin/python index_repos.py --repo my-project
```

Wait for the indexer to finish (you will see output in the proxy logs or terminal). For a small project this takes a few seconds; larger repos take longer.

---

### 4. Confirm the repo is visible

Open Cline in VS Code and ask it to list available repos:

```
Call list_repos
```

`my-project` should appear in the response. If it does not, check that the repo is directly under `REPO_ROOT` (not nested inside a subdirectory).

---

### 5. Confirm context injection is working

Ask Cline a question that requires knowledge of your codebase:

```
What files are in my-project and what do they do?
```

The proxy will inject relevant code chunks from ChromaDB into the request. If the response is accurate about your actual files, context injection is working.

If the proxy is running but returning no context, run the indexer again (step 3) and check the proxy logs for `[proxy] no context found` messages.

---

### 6. Confirm verification works

```
Call verify_project for my-project
```

The tool auto-detects the stack from your repo contents:

| What it finds | What it runs |
|---|---|
| `tsconfig.json` or `typescript` in `package.json` | `tsc --noEmit` |
| `react` in `package.json` | `tsc --noEmit` + ESLint (if configured) |
| `react-native` in `package.json` | `tsc --noEmit` + ESLint (if configured) |
| `CMakeLists.txt` | `cmake --build build/` |
| `Makefile` | `make -j4` |

If the stack is not detected, check that the relevant config files (`package.json`, `tsconfig.json`, `CMakeLists.txt`) are at the repo root.

---

### 7. (Optional) Add documentation sources

If your project uses a framework that is not already indexed (React, TypeScript, and Next.js are included by default), add it to `config.py` and run the doc indexer.

See [ADDING-DOCS.md](ADDING-DOCS.md) for the full process.

---

## That's it

From this point on:

- **File changes** are picked up automatically by the file watcher — no manual reindex needed
- **New repos** added under `REPO_ROOT` are detected at proxy startup, or after a proxy restart
- **Cline context** is injected automatically on every request — no prompt changes needed
- **Verification** is available on any project via `verify_project`

The only per-project setup is the clinerules file. Everything else is automatic.

---

## Quick reference — commands

```bash
# Check the repo is in the right place
ls /home/yourname/mcp-context/repos

# Trigger a manual re-index
curl -X POST "http://localhost:8000/reindex?repo=my-project"

# Run the indexer directly
cd /mnt/storage/mcp-tools && .venv/bin/python index_repos.py --repo my-project

# Check proxy is running
curl http://localhost:8000/v1/models
```
