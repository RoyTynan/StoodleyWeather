"""
File watcher — monitors all repos under REPO_ROOT and triggers incremental
reindexing when indexable files change. One reindex per repo per debounce window.
"""

import subprocess
import sys
import time
import threading
import logging
from watchfiles import watch
from config import REPO_ROOT, INDEXABLE_EXTENSIONS, EXCLUDED_DIRS, TOOLS_DIR, VENV_PYTHON

DEBOUNCE_SECONDS = 10

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def repo_from_path(path: str) -> str | None:
    """Extract repo name from an absolute file path under REPO_ROOT."""
    if not path.startswith(REPO_ROOT + "/"):
        return None
    rel = path[len(REPO_ROOT) + 1:]
    parts = rel.split("/")
    return parts[0] if parts else None


def is_indexable(path: str) -> bool:
    parts = path.split("/")
    if any(part in EXCLUDED_DIRS for part in parts):
        return False
    return any(path.endswith(ext) for ext in INDEXABLE_EXTENSIONS)


def reindex(repo: str):
    log.info("Reindexing %s ...", repo)
    result = subprocess.run(
        [VENV_PYTHON, f"{TOOLS_DIR}/index_repos.py", "--repo", repo],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        log.info("Reindex complete: %s", repo)
    else:
        log.error("Reindex failed for %s: %s", repo, result.stderr.strip())


def _debounced_reindex(repo: str, timers: dict):
    def _run():
        timers.pop(repo, None)
        reindex(repo)
    if repo in timers:
        timers[repo].cancel()
    t = threading.Timer(DEBOUNCE_SECONDS, _run)
    timers[repo] = t
    t.start()


def main():
    log.info("Watching %s for changes ...", REPO_ROOT)
    timers: dict[str, threading.Timer] = {}

    for changes in watch(REPO_ROOT):
        for _, path in changes:
            if not is_indexable(path):
                continue
            repo = repo_from_path(path)
            if repo:
                log.info("Change detected in %s — reindex in %ds", repo, DEBOUNCE_SECONDS)
                _debounced_reindex(repo, timers)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
