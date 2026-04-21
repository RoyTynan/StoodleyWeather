# Auto-Indexing Repos into ChromaDB

## Overview

The `watcher.py` service monitors all repos under `REPO_ROOT` and automatically reindexes
them into ChromaDB whenever indexable files change. This keeps the RAG context always up
to date without manual intervention.

---

## How It Works

1. `watcher.py` uses `watchfiles` to watch `/home/roy/mcp-context/repos` recursively
2. When a file change is detected, it extracts the repo name from the path
3. A 10-second debounce timer is started for that repo — further changes within the window reset the timer
4. After 10 seconds of inactivity, `index_repos.py --repo <repo>` is called to reindex only that repo
5. The service runs as a systemd unit (`mcp-indexer.service`) and starts automatically on boot

---

## File Types Indexed

Controlled by `INDEXABLE_EXTENSIONS` in `config.py`:

```python
INDEXABLE_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".css", ".json", ".md", ".py", ".cpp", ".h", ".c"}
```

`.md` was added to allow project documentation to be semantically searchable.
`.py`, `.cpp`, `.h`, `.c` were added so Python and C/C++ projects are indexed alongside web projects.

---

## Excluding Files Per Repo

Each repo can have a `.chromaignore` file in its root to exclude specific files or folders
from indexing. One pattern per line, `#` for comments.

Example — index only `docs/*.md`, exclude all other markdown:

```
# Exclude all .md files except docs/
README.md
frontend/README.md
.clinerules/*.md
backend/**/*.md
```

The `.chromaignore` logic supports glob patterns via `fnmatch`. It does **not** support
negation (`!`) — use exclusion patterns for everything you don't want indexed.

---

## Systemd Service

**File:** `/etc/systemd/system/mcp-indexer.service`

```ini
[Unit]
Description=MCP repo auto-indexer
After=network.target

[Service]
Type=simple
User=roy
ExecStart=/mnt/storage/mcp-tools/.venv/bin/python /mnt/storage/mcp-tools/watcher.py
WorkingDirectory=/mnt/storage/mcp-tools
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Commands

```bash
# Enable and start
sudo systemctl enable mcp-indexer
sudo systemctl start mcp-indexer

# Check status
sudo systemctl status mcp-indexer

# View live logs
journalctl -u mcp-indexer -f

# Restart after config changes
sudo systemctl restart mcp-indexer
```

---

## Manual Reindex

To force a full reindex of a specific repo:

```bash
python /mnt/storage/mcp-tools/index_repos.py --repo <repo-name>
```

To reindex all repos:

```bash
python /mnt/storage/mcp-tools/index_repos.py
```

---

## Adding a New Repo

No configuration needed. Any repo placed under `/home/roy/mcp-context/repos` is watched
and indexed automatically. Add a `.chromaignore` if you want to exclude specific files.
