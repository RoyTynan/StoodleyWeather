# Adding Documentation Libraries to the RAG System

This document covers how to add a new documentation library to the local AI setup — downloading the source, indexing it into ChromaDB, adding a search tool to the MCP server, and wiring it into the clinerules so Cline knows to use it.

Three libraries are documented here: React, TypeScript, and Next.js.

> **Path convention:** This document uses `/mnt/storage/` as the base storage path and `/mnt/storage/mcp-tools/` as the MCP tools directory. These match the layout described in [AI-SETUP.md](AI-SETUP.md). Replace them with wherever you have placed these directories on your own machine.

---

## How it works

There are two ways docs are searched in this setup:

| Method | How | Used for |
|---|---|---|
| **Ripgrep** | Keyword search over files on disk | React |
| **ChromaDB semantic search** | Vector similarity search via `search_*` tools | TypeScript, Next.js, and any other large API surface |

Ripgrep is fast and exact — good for framework docs written in Markdown where you know the keyword. ChromaDB semantic search lets you query by concept ("how do I do X") rather than exact keyword — better for large API surfaces.

---

## React Docs

React docs are searched via ripgrep using the `search_official_docs` tool in `server.py`. No ChromaDB indexing is needed.

### 1. Download

```bash
git clone https://github.com/reactjs/react.dev.git /mnt/storage/docs/frameworks/react-docs
```

The docs are Markdown files under `src/content/`.

### 2. No indexing needed

`search_official_docs` calls ripgrep directly on the file system. Skip the ChromaDB step.

### 3. Add tool to `server.py`

Add a tool that calls ripgrep over the cloned directory:

```python
@mcp.tool()
def search_official_docs(query: str) -> str:
    """Search official React documentation using ripgrep."""
    path = "/mnt/storage/docs/frameworks/react-docs/src/content"
    result = subprocess.run(
        ["rg", "-i", "--heading", "-m", "3", query, path],
        capture_output=True, text=True
    )
    return result.stdout or "No results found."
```

### 4. Clinerules

In `.clinerules/search.md`, add to the tool reference table:

```
| `search_official_docs` | React 19 docs (ripgrep) |
```

And in the server-to-tool mapping:

```
| `search_official_docs` | `context-engine` |
```

---

## TypeScript Docs

TypeScript docs are indexed into ChromaDB and searched semantically via `search_typescript_docs`.

### 1. Download

Sparse clone — pulls only the handbook and tsconfig reference, not the full TypeScript-Website monorepo:

```bash
git clone --depth=1 --filter=blob:none --sparse \
  https://github.com/microsoft/TypeScript-Website.git \
  /mnt/storage/docs/frameworks/typescript-docs

git -C /mnt/storage/docs/frameworks/typescript-docs sparse-checkout set \
  packages/documentation/copy/en \
  packages/tsconfig-reference
```

### 2. Add to `index_docs.py`

In `DOCS_SOURCES`, add:

```python
"typescript": [
    "/mnt/storage/docs/frameworks/typescript-docs/packages/documentation/copy/en",
    "/mnt/storage/docs/frameworks/typescript-docs/packages/tsconfig-reference",
],
```

### 3. Run the indexer

```bash
cd /mnt/storage/mcp-tools
.venv/bin/python index_docs.py --lib typescript
```

This creates the ChromaDB collection `docs_typescript`. On first run it will embed all chunks — expect a few minutes.

### 4. Add tool to `docs_server.py`

```python
@mcp.tool()
def search_typescript_docs(query: str, n_results: int = 8, repo_name: str = "", task_progress: str = "") -> str:
    """Semantic search over TypeScript documentation and handbook.
    Find type system features, compiler options and language reference."""
    return _search("docs_typescript", query, n_results,
                   "TypeScript docs index not found. Run: python /mnt/storage/mcp-tools/index_docs.py --lib typescript")
```

### 5. Clinerules

In `.clinerules/search.md`, add to the tool reference table:

```
| `search_typescript_docs` | TypeScript handbook and tsconfig reference |
```

And in the server-to-tool mapping:

```
| `search_typescript_docs` | `docs-engine` |
```

---

## Next.js Docs

Next.js docs are indexed into ChromaDB and searched semantically via `search_nextjs_docs`.

### 1. Download

The Next.js docs live in the main `vercel/next.js` repo under `docs/`. Sparse clone that folder only:

```bash
git clone --depth=1 --filter=blob:none --sparse \
  https://github.com/vercel/next.js.git \
  /mnt/storage/docs/frameworks/nextjs-docs

git -C /mnt/storage/docs/frameworks/nextjs-docs sparse-checkout set docs
```

### 2. Add to `index_docs.py`

In `DOCS_SOURCES`, add:

```python
"nextjs": [
    "/mnt/storage/docs/frameworks/nextjs-docs/docs",
],
```

### 3. Run the indexer

```bash
cd /mnt/storage/mcp-tools
.venv/bin/python index_docs.py --lib nextjs
```

This creates the ChromaDB collection `docs_nextjs`.

### 4. Add tool to `docs_server.py`

```python
@mcp.tool()
def search_nextjs_docs(query: str, n_results: int = 8, repo_name: str = "", task_progress: str = "") -> str:
    """Semantic search over Next.js documentation.
    Find routing, data fetching, rendering, API routes and configuration by describing what you need."""
    return _search("docs_nextjs", query, n_results,
                   "Next.js docs index not found. Run: python /mnt/storage/mcp-tools/index_docs.py --lib nextjs")
```

### 5. Clinerules

In `.clinerules/search.md`, add to the tool reference table:

```
| `search_nextjs_docs` | Next.js routing, data fetching, rendering, API routes, config |
```

And in the server-to-tool mapping:

```
| `search_nextjs_docs` | `docs-engine` |
```

### 6. Reload VS Code

After updating `docs_server.py`, reload VS Code so Cline restarts the MCP server and picks up the new tool.

---

## General Pattern

Every new ChromaDB documentation library follows the same five steps:

1. **Download** — sparse clone or full clone to `/mnt/storage/docs/frameworks/<name>-docs/`
2. **Add to `DOCS_SOURCES`** in `index_docs.py` — map the library name to its file paths
3. **Run indexer** — `python index_docs.py --lib <name>` — creates `docs_<name>` collection
4. **Add tool** to `docs_server.py` — copy an existing tool, change the collection name and docstring
5. **Update clinerules** — add the tool to the search.md reference table and server mapping

To update docs after pulling new source:

```bash
git -C /mnt/storage/docs/frameworks/<name>-docs pull
.venv/bin/python index_docs.py --lib <name>
```

The indexer only re-embeds changed files (hash-based manifest), so incremental updates are fast.
