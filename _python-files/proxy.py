"""
LLM Proxy — sits between Cline and the i9 llama-server.
Intercepts /v1/chat/completions requests, enriches the prompt
with relevant code chunks from ChromaDB, then forwards to the LLM.

Watches all repos under REPO_ROOT for file changes and triggers
re-indexing automatically. Multi-repo aware — detects the active
repo from conversation context and queries the right collection.

Configure the addresses and paths below to match your setup.
"""

import os
import subprocess
import threading
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import chromadb
from chromadb.config import Settings
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import (
    LLM_URL, CHROMA_DIR, REPO_ROOT, EMBED_URL,
    INDEX_SCRIPT, VENV_PYTHON, N_CONTEXT_CHUNKS,
    INDEXABLE_EXTENSIONS, EXCLUDED_DIRS,
)

app = FastAPI()

_chroma_client = chromadb.PersistentClient(
    path=CHROMA_DIR,
    settings=Settings(anonymized_telemetry=False),
)

_http_client = httpx.Client(timeout=120.0)

# Per-repo debounce timers
_reindex_timers: dict[str, threading.Timer] = {}
_reindex_lock = threading.Lock()


def get_repos() -> list[str]:
    """Return all repo directory names under REPO_ROOT."""
    try:
        return [
            d for d in os.listdir(REPO_ROOT)
            if os.path.isdir(os.path.join(REPO_ROOT, d))
        ]
    except OSError:
        return []


def trigger_reindex(repo_name: str):
    """Run index_repos.py for the given repo."""
    print(f"[watcher] re-indexing {repo_name}...")
    result = subprocess.run(
        [VENV_PYTHON, INDEX_SCRIPT, "--repo", repo_name],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"[watcher] re-index complete for {repo_name}")
    else:
        print(f"[watcher] re-index error for {repo_name}: {result.stderr.strip()}")


def schedule_reindex(repo_name: str):
    """Debounce re-index — wait 3s after last change before running."""
    with _reindex_lock:
        existing = _reindex_timers.get(repo_name)
        if existing is not None:
            existing.cancel()
        timer = threading.Timer(3.0, trigger_reindex, args=[repo_name])
        timer.start()
        _reindex_timers[repo_name] = timer


class RepoChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        self._handle(event.src_path)

    def on_created(self, event):
        if event.is_directory:
            return
        self._handle(event.src_path)

    def _handle(self, path: str):
        for excluded in EXCLUDED_DIRS:
            if f"/{excluded}/" in path:
                return
        ext = path.rsplit(".", 1)[-1] if "." in path else ""
        if f".{ext}" not in INDEXABLE_EXTENSIONS:
            return
        # Extract repo name from path: REPO_ROOT/repo_name/...
        rel = path.replace(REPO_ROOT + "/", "")
        parts = rel.split("/")
        if len(parts) < 2:
            return
        repo_name = parts[0]
        rel_path = "/".join(parts[1:])
        print(f"[watcher] file changed: {repo_name}/{rel_path}")
        schedule_reindex(repo_name)


def start_file_watcher():
    handler = RepoChangeHandler()
    observer = Observer()
    observer.schedule(handler, path=REPO_ROOT, recursive=True)
    observer.start()
    print(f"[watcher] watching {REPO_ROOT}")


def get_embedding(text: str) -> list:
    response = _http_client.post(
        EMBED_URL,
        json={"model": "nomic-embed-text", "input": f"search_query: {text}"},
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def detect_repo(messages: list) -> str | None:
    """Scan messages from most recent to detect which repo is being worked on."""
    repos = get_repos()
    if not repos:
        return None
    for msg in reversed(messages):
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        for repo in repos:
            if repo in content:
                return repo
    return None


def fetch_relevant_chunks(query: str, repo_name: str) -> str:
    try:
        collection = _chroma_client.get_collection(f"repo_{repo_name}")
        vector = get_embedding(query)
        results = collection.query(query_embeddings=[vector], n_results=N_CONTEXT_CHUNKS)
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        if not docs:
            return ""
        parts = []
        for doc, meta in zip(docs, metas):
            print(f"[proxy] chunk: {meta['file_path']} lines {meta['start_line']}–{meta['end_line']}")
            parts.append(f"// {meta['file_path']} (lines {meta['start_line']}–{meta['end_line']})\n{doc.strip()}")
        return "\n\n".join(parts)
    except Exception:
        return ""


def enrich_messages(messages: list) -> list:
    """Inject relevant code chunks before the last user message."""
    if not messages:
        return messages

    last_user_idx = None
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            last_user_idx = i
            break

    if last_user_idx is None:
        return messages

    user_content = messages[last_user_idx].get("content", "")

    # Skip enrichment if prompt references a specific file path —
    # Cline will read the file directly via MCP, avoiding format mismatch.
    if "src/" in user_content:
        print("[proxy] skipping enrichment — specific file path detected in prompt")
        return messages

    repo_name = detect_repo(messages)
    if repo_name is None:
        print("[proxy] no repo detected in conversation, skipping enrichment")
        return messages

    chunks = fetch_relevant_chunks(user_content, repo_name)

    if chunks:
        print(f"[proxy] injecting {N_CONTEXT_CHUNKS} chunks from {repo_name} for: {user_content[:80]}")
        enriched_content = (
            f"Relevant code from the project:\n\n{chunks}\n\n"
            f"---\n\n{user_content}"
        )
        messages = list(messages)
        messages[last_user_idx] = {**messages[last_user_idx], "content": enriched_content}
    else:
        print(f"[proxy] no chunks found in {repo_name} for: {user_content[:80]}")

    return messages


@app.on_event("startup")
async def startup():
    repos = get_repos()
    print(f"[proxy] repos found: {repos}")
    start_file_watcher()


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    body["messages"] = enrich_messages(body.get("messages", []))

    stream = body.get("stream", False)

    if stream:
        def generate():
            with _http_client.stream(
                "POST",
                f"{LLM_URL}/v1/chat/completions",
                json=body,
                timeout=120.0,
            ) as r:
                for chunk in r.iter_bytes():
                    yield chunk

        return StreamingResponse(generate(), media_type="text/event-stream")
    else:
        response = _http_client.post(f"{LLM_URL}/v1/chat/completions", json=body)
        return JSONResponse(content=response.json(), status_code=response.status_code)


@app.post("/reindex")
async def reindex(repo: str | None = None):
    """Force a re-index. Pass ?repo=name for a specific repo, or reindex all."""
    if repo:
        threading.Thread(target=trigger_reindex, args=[repo], daemon=True).start()
        return JSONResponse(content={"status": "re-index started", "repo": repo})
    else:
        repos = get_repos()
        for r in repos:
            threading.Thread(target=trigger_reindex, args=[r], daemon=True).start()
        return JSONResponse(content={"status": "re-index started", "repos": repos})


@app.get("/v1/models")
async def list_models():
    """Pass model list through from the LLM server."""
    response = _http_client.get(f"{LLM_URL}/v1/models")
    return JSONResponse(content=response.json(), status_code=response.status_code)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
