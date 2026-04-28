"""
LLM Proxy — sits between Cline and the i9 llama-server.
Intercepts /v1/chat/completions requests, enriches the prompt
with relevant code chunks from ChromaDB, then forwards to the LLM.

Watches all repos under REPO_ROOT for file changes and triggers
re-indexing automatically. Multi-repo aware — detects the active
repo from conversation context and queries the right collection.

Configure the addresses and paths below to match your setup.
"""

import json
import os
import re
import sqlite3
import subprocess
import threading
import uuid
from datetime import datetime, timezone
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import chromadb
from chromadb.config import Settings
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from rank_bm25 import BM25Okapi
from config import (
    LLM_URL, CHROMA_DIR, REPO_ROOT, EMBED_URL, EMBED_QUERY_PREFIX,
    INDEX_SCRIPT, VENV_PYTHON, N_CONTEXT_CHUNKS,
    INDEXABLE_EXTENSIONS, EXCLUDED_DIRS, SKELETON_MAX_FILES,
    CHUNK_CHARS, CHUNK_OVERLAP,
    DEP_GRAPH_ENABLED, DEP_GRAPH_DB, MAX_IMPACT_FILES,
    LLM_HAS_THINKING,
)
from rerank import rerank
from verify import verify

from contextlib import asynccontextmanager

PROMPT_LOG_DB = "/mnt/storage/prompt_log.db"

_db_conn: sqlite3.Connection | None = None
_db_lock = threading.Lock()


def _init_db():
    global _db_conn
    _db_conn = sqlite3.connect(PROMPT_LOG_DB, check_same_thread=False)
    _db_conn.execute("""
        CREATE TABLE IF NOT EXISTS prompts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT    NOT NULL,
            repo            TEXT,
            raw_query       TEXT,
            enriched_message TEXT,
            full_messages   TEXT,
            skeleton_injected INTEGER,
            chunks_injected   INTEGER,
            verify_injected   INTEGER,
            finish_reason   TEXT,
            response_text   TEXT,
            latency_ms      INTEGER
        )
    """)
    # Migrate existing DBs that predate response_text / latency_ms columns
    existing = {row[1] for row in _db_conn.execute("PRAGMA table_info(prompts)")}
    for col, definition in [
        ("response_text", "TEXT"), ("latency_ms", "INTEGER"), ("model", "TEXT"),
        ("task_id", "TEXT"), ("step_type", "TEXT"), ("user_task", "TEXT"),
        ("prompt_tokens", "INTEGER"), ("completion_tokens", "INTEGER"),
    ]:
        if col not in existing:
            _db_conn.execute(f"ALTER TABLE prompts ADD COLUMN {col} {definition}")
    _db_conn.execute("""
        CREATE TABLE IF NOT EXISTS config_snapshots (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT    NOT NULL,
            config    TEXT    NOT NULL
        )
    """)
    _db_conn.commit()
    print(f"[db] prompt log: {PROMPT_LOG_DB}")


def _snapshot_config():
    if _db_conn is None:
        return
    snapshot = json.dumps({
        "LLM_URL": LLM_URL,
        "EMBED_URL": EMBED_URL,
        "REPO_ROOT": REPO_ROOT,
        "CHROMA_DIR": CHROMA_DIR,
        "N_CONTEXT_CHUNKS": N_CONTEXT_CHUNKS,
        "SKELETON_MAX_FILES": SKELETON_MAX_FILES,
        "CHUNK_CHARS": CHUNK_CHARS,
        "CHUNK_OVERLAP": CHUNK_OVERLAP,
        "DEP_GRAPH_ENABLED": DEP_GRAPH_ENABLED,
        "MAX_IMPACT_FILES": MAX_IMPACT_FILES,
        "LLM_HAS_THINKING": LLM_HAS_THINKING,
    })
    with _db_lock:
        _db_conn.execute(
            "INSERT INTO config_snapshots (timestamp, config) VALUES (?, ?)",
            (datetime.now(timezone.utc).isoformat(), snapshot),
        )
        _db_conn.commit()
    print("[db] config snapshot written")


def _log_prompt(meta: dict, full_messages: list, finish_reason: str | None) -> int | None:
    if _db_conn is None:
        return None
    with _db_lock:
        cur = _db_conn.execute(
            """INSERT INTO prompts
               (timestamp, repo, raw_query, enriched_message, full_messages,
                skeleton_injected, chunks_injected, verify_injected, finish_reason,
                task_id, step_type, user_task)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                meta.get("repo"),
                meta.get("raw_query"),
                meta.get("enriched_message"),
                json.dumps(full_messages),
                int(meta.get("skeleton_injected", False)),
                int(meta.get("chunks_injected", False)),
                int(meta.get("verify_injected", False)),
                finish_reason,
                meta.get("task_id"),
                meta.get("step_type"),
                meta.get("user_task"),
            ),
        )
        _db_conn.commit()
        return cur.lastrowid


def _update_log_response(
    log_id: int, response_text: str, finish_reason: str | None, latency_ms: int,
    model: str | None = None, prompt_tokens: int | None = None,
    completion_tokens: int | None = None, step_type_override: str | None = None,
):
    if _db_conn is None or log_id is None:
        return
    with _db_lock:
        _db_conn.execute(
            """UPDATE prompts
               SET response_text=?, finish_reason=?, latency_ms=?, model=?,
                   prompt_tokens=?, completion_tokens=?
                   {step_override}
               WHERE id=?""".format(
                step_override=", step_type=?" if step_type_override else ""
            ),
            (
                *(
                    (response_text, finish_reason, latency_ms, model,
                     prompt_tokens, completion_tokens, step_type_override, log_id)
                    if step_type_override else
                    (response_text, finish_reason, latency_ms, model,
                     prompt_tokens, completion_tokens, log_id)
                ),
            ),
        )
        _db_conn.commit()


def _extract_streaming_response(chunks: list[bytes]) -> tuple[str, str | None, int | None, int | None]:
    """Reconstruct assistant text, model, and token counts from buffered SSE chunks."""
    parts = []
    model = None
    prompt_tokens = None
    completion_tokens = None
    for chunk in chunks:
        try:
            for line in chunk.decode("utf-8", errors="ignore").splitlines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    data = json.loads(line[6:])
                    if model is None:
                        model = data.get("model")
                    usage = data.get("usage") or {}
                    if usage.get("prompt_tokens"):
                        prompt_tokens = usage["prompt_tokens"]
                    if usage.get("completion_tokens"):
                        completion_tokens = usage["completion_tokens"]
                    content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        parts.append(content)
        except Exception:
            pass
    return "".join(parts), model, prompt_tokens, completion_tokens


_HALT_MSG = (
    "[PROXY HALT] The LLM returned an empty response — likely context window saturation. "
    "Stop this task and start a new one with a more focused prompt."
)

# Cline parses attempt_completion as a terminal tool call — task ends cleanly,
# context is cleared, and the user sees the result message without a retry loop.
_HALT_CLINE_CONTENT = """\
<attempt_completion>
<result>
Proxy halted this task: the model returned an empty response, which means the \
context window is saturated.

Please start a new Cline task with a more specific prompt. Examples:
  - "Fix the bug in src/api/weather.ts"
  - "Explain how src/components/WeatherChart.tsx works"
  - "Add X feature to src/app/page.tsx"

Avoid broad instructions like "read the entire project" — the proxy already \
injects the relevant context automatically.
</result>
</attempt_completion>"""

_LLM_DOWN_MSG = "[PROXY ERROR] LLM server unreachable at {url}. Check that the i9 is running."

_LLM_DOWN_CLINE_CONTENT = """\
<attempt_completion>
<result>
The LLM server is not reachable ({url}).

Start the LLM on the i9 and retry:
  bash start-llm.sh
</result>
</attempt_completion>"""

_pending_halt: dict[str, bool] = {}


def _do_halt(log_id: int | None, latency_ms: int, task_id: str | None):
    """Log a HALT and mark the task so the next request is also blocked."""
    print(f"[proxy] HALT — empty LLM response for task {task_id}")
    if log_id is not None:
        _update_log_response(log_id, _HALT_MSG, "halt", latency_ms, step_type_override="HALT")
    if task_id:
        _pending_halt[task_id] = True


def _do_llm_down(log_id: int | None, latency_ms: int):
    """Log an LLM-unreachable error. Does not block the next request — server may come back up."""
    msg = _LLM_DOWN_MSG.format(url=LLM_URL)
    print(f"[proxy] ERROR — {msg}")
    if log_id is not None:
        _update_log_response(log_id, msg, "error", latency_ms, step_type_override="ERROR")


def _halt_json_response() -> JSONResponse:
    return JSONResponse(content={
        "id": "proxy-halt",
        "object": "chat.completion",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": _HALT_CLINE_CONTENT},
            "finish_reason": "stop",
        }],
        "model": "proxy-halt",
    }, status_code=200)


def _llm_down_json_response() -> JSONResponse:
    content = _LLM_DOWN_CLINE_CONTENT.format(url=LLM_URL)
    return JSONResponse(content={
        "id": "proxy-error",
        "object": "chat.completion",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "model": "proxy-error",
    }, status_code=200)


def _llm_down_sse_chunks(url: str):
    content = _LLM_DOWN_CLINE_CONTENT.format(url=url)
    payload = json.dumps({
        "id": "proxy-error",
        "object": "chat.completion.chunk",
        "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": "stop"}],
        "model": "proxy-error",
    })
    yield f"data: {payload}\n\n".encode()
    yield b"data: [DONE]\n\n"


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_db()
    _snapshot_config()
    repos = get_repos()
    print(f"[proxy] repos found: {repos}")
    for repo in repos:
        build_bm25_index(repo)
        build_skeleton(repo)
    start_file_watcher()
    yield

app = FastAPI(lifespan=lifespan)

_chroma_client = chromadb.PersistentClient(
    path=CHROMA_DIR,
    settings=Settings(anonymized_telemetry=False),
)

_http_client = httpx.Client(timeout=120.0)

# Per-repo debounce timers
_reindex_timers: dict[str, threading.Timer] = {}
_reindex_lock = threading.Lock()

# Per-repo BM25 indices — rebuilt after every re-index
_bm25_indices: dict[str, BM25Okapi] = {}
_bm25_corpus: dict[str, tuple[list[str], list[dict]]] = {}  # (docs, metas)
_bm25_lock = threading.Lock()

# Per-repo skeleton maps — rebuilt after every re-index
_repo_skeletons: dict[str, str] = {}
_skeleton_lock = threading.Lock()

# Regex patterns for extracting exported symbols from TS/JS files
_EXPORT_PATTERNS = [
    re.compile(r'export\s+(?:async\s+)?function\s+(\w+)'),
    re.compile(r'export\s+const\s+(\w+)\s*[=:(]'),
    re.compile(r'export\s+(?:type|interface|class|enum)\s+(\w+)'),
    re.compile(r'export\s+default\s+(?:async\s+)?(?:function|class)\s+(\w+)'),
]

RRF_K = 60              # RRF constant — higher = smoother rank blending
CANDIDATE_POOL = N_CONTEXT_CHUNKS * 3  # candidates fetched from each search method

# Pending verification results — written by background thread, consumed by enrich_messages
_pending_verify: dict[str, str] = {}

# Pending impact analysis — keyed by task_id, consumed on next enriched prompt
_pending_impact: dict[str, str] = {}

# Matches Cline tool result messages that indicate a file was written
_FILE_WRITE_PATTERN = re.compile(
    r'\[\s*(?:write_to_file|replace_in_file|create_file)\s+for\s+[\'"]',
    re.IGNORECASE,
)

# Extracts the file path from a write tool result message
_WRITE_PATH_RE = re.compile(
    r'\[\s*(?:write_to_file|replace_in_file|create_file)\s+for\s+[\'"]([^\'"]+)[\'"]',
    re.IGNORECASE,
)


def _get_impact(repo_name: str, edited_file: str) -> str | None:
    """Query dep_graph.db for files that import edited_file. Returns a formatted note or None."""
    if not DEP_GRAPH_ENABLED:
        return None
    try:
        conn = sqlite3.connect(DEP_GRAPH_DB, check_same_thread=False)
        rows = conn.execute(
            "SELECT DISTINCT file FROM edges WHERE repo = ? AND imports_file = ? LIMIT ?",
            (repo_name, edited_file, MAX_IMPACT_FILES + 1),
        ).fetchall()
        conn.close()
    except Exception as e:
        print(f"[dep_graph] query error: {e}")
        return None
    if not rows:
        return None
    files = [row[0] for row in rows[:MAX_IMPACT_FILES]]
    truncated = len(rows) > MAX_IMPACT_FILES
    note = f"Dependency impact: `{edited_file}` is also imported by:\n"
    note += "\n".join(f"  - {f}" for f in files)
    if truncated:
        note += f"\n  - … (capped at {MAX_IMPACT_FILES})"
    return note

# Strip Qwen3 thinking blocks before returning content to Cline
_THINK_RE = re.compile(r'<think>.*?</think>', re.DOTALL)

# Task and step detection
_TASK_TAG = re.compile(r'<task>(.*?)</task>', re.DOTALL)
_WRITE_STEP = re.compile(r'^\[\s*(?:write_to_file|replace_in_file|create_file)\b', re.IGNORECASE)

_current_task_id: str | None = None
_task_id_lock = threading.Lock()


def _detect_step(content: str) -> tuple[str, str | None, str | None]:
    """Classify a user message. Returns (step_type, task_id, user_task)."""
    global _current_task_id

    task_match = _TASK_TAG.search(content)
    if task_match:
        new_id = str(uuid.uuid4())
        with _task_id_lock:
            _current_task_id = new_id
        return 'TASK', new_id, task_match.group(1).strip()

    with _task_id_lock:
        task_id = _current_task_id

    s = content.lstrip()
    if s.startswith('[read_file'):
        return 'READ', task_id, None
    if _WRITE_STEP.match(s):
        return 'WRITE', task_id, None
    if s.startswith('[execute_command'):
        return 'CMD', task_id, None
    if s.startswith('[ERROR]'):
        return 'ERROR', task_id, None
    if s.startswith('[attempt_completion]'):
        return 'DONE', task_id, None
    if s.startswith('[ask_followup_question'):
        return 'FOLLOWUP', task_id, None
    if s.startswith('['):
        return 'TOOL', task_id, None

    return 'PROMPT', task_id, None


def _schedule_verify(repo_name: str):
    """Run verify in a background thread and store the result for the next prompt."""
    def run():
        repo_path = os.path.join(REPO_ROOT, repo_name)
        try:
            result = verify(repo_path, repo_name)
            _pending_verify[repo_name] = result.summary()
            status = "PASS" if result.passed else "FAIL"
            print(f"[proxy] auto-verify {status} for {repo_name}")
        except Exception as e:
            print(f"[proxy] auto-verify error for {repo_name}: {e}")
    threading.Thread(target=run, daemon=True).start()


def get_repos() -> list[str]:
    """Return all repo directory names under REPO_ROOT."""
    try:
        return [
            d for d in os.listdir(REPO_ROOT)
            if os.path.isdir(os.path.join(REPO_ROOT, d))
        ]
    except OSError:
        return []


def build_bm25_index(repo_name: str):
    """Build in-memory BM25 index from all chunks stored in ChromaDB for a repo."""
    try:
        collection = _chroma_client.get_collection(f"repo_{repo_name}")
        total = collection.count()
        if total == 0:
            print(f"[bm25] no documents for {repo_name}")
            return
        docs: list[str] = []
        metas: list[dict] = []
        batch = 500
        for offset in range(0, total, batch):
            results = collection.get(limit=batch, offset=offset)
            docs.extend(results["documents"])
            metas.extend(results["metadatas"])
        tokenized = [doc.lower().split() for doc in docs]
        with _bm25_lock:
            _bm25_indices[repo_name] = BM25Okapi(tokenized)
            _bm25_corpus[repo_name] = (docs, metas)
        print(f"[bm25] index built for {repo_name} ({len(docs)} chunks)")
    except Exception as e:
        print(f"[bm25] failed to build index for {repo_name}: {e}")


def build_skeleton(repo_name: str):
    """Build a compact per-repo skeleton: one line per file listing exported symbols."""
    repo_path = os.path.join(REPO_ROOT, repo_name)
    lines = []
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for filename in sorted(filenames):
            ext = os.path.splitext(filename)[1]
            if ext not in INDEXABLE_EXTENSIONS:
                continue
            abs_path = os.path.join(dirpath, filename)
            rel_path = abs_path.replace(repo_path + "/", "")
            try:
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            symbols = []
            for pattern in _EXPORT_PATTERNS:
                symbols.extend(pattern.findall(content))
            if symbols:
                lines.append(f"{rel_path} → {', '.join(dict.fromkeys(symbols))}")
            if len(lines) >= SKELETON_MAX_FILES:
                break
        if len(lines) >= SKELETON_MAX_FILES:
            break
    if not lines:
        print(f"[skeleton] no symbols found for {repo_name}")
        return
    skeleton = "\n".join(lines)
    with _skeleton_lock:
        _repo_skeletons[repo_name] = skeleton
    print(f"[skeleton] built for {repo_name} ({len(lines)} files)")


def trigger_reindex(repo_name: str):
    """Run index_repos.py for the given repo, then rebuild the BM25 index."""
    print(f"[watcher] re-indexing {repo_name}...")
    result = subprocess.run(
        [VENV_PYTHON, INDEX_SCRIPT, "--repo", repo_name],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"[watcher] re-index complete for {repo_name}")
        build_bm25_index(repo_name)
        build_skeleton(repo_name)
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
        json={"model": "bge-m3", "input": f"{EMBED_QUERY_PREFIX}{text}"},
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


def hybrid_search(query: str, repo_name: str) -> str:
    """Hybrid search combining ChromaDB vector search and BM25 keyword search via RRF."""

    # --- Vector search — semantic similarity ---
    vector_results: list[tuple[str, dict]] = []
    try:
        collection = _chroma_client.get_collection(f"repo_{repo_name}")
        vector = get_embedding(query)
        results = collection.query(query_embeddings=[vector], n_results=CANDIDATE_POOL)
        vector_results = list(zip(results["documents"][0], results["metadatas"][0]))
    except Exception:
        pass

    # --- BM25 search — exact keyword matching ---
    bm25_results: list[tuple[str, dict]] = []
    with _bm25_lock:
        index = _bm25_indices.get(repo_name)
        corpus = _bm25_corpus.get(repo_name)
    if index is not None and corpus is not None:
        all_docs, all_metas = corpus
        scores = index.get_scores(query.lower().split())
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:CANDIDATE_POOL]
        bm25_results = [(all_docs[i], all_metas[i]) for i in top_indices if scores[i] > 0]

    if not vector_results and not bm25_results:
        return ""

    # --- Reciprocal Rank Fusion ---
    rrf_scores: dict[tuple, float] = {}
    chunk_map: dict[tuple, tuple[str, dict]] = {}

    for rank, (doc, meta) in enumerate(vector_results):
        key = (meta["file_path"], meta["start_line"])
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (RRF_K + rank + 1)
        chunk_map[key] = (doc, meta)

    for rank, (doc, meta) in enumerate(bm25_results):
        key = (meta["file_path"], meta["start_line"])
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (RRF_K + rank + 1)
        chunk_map[key] = (doc, meta)

    all_keys = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)
    all_chunks = [(chunk_map[k][0], chunk_map[k][1]) for k in all_keys]
    reranked = rerank(query, all_chunks, top_n=N_CONTEXT_CHUNKS)

    parts = []
    for doc, meta in reranked:
        print(f"[proxy] chunk: {meta['file_path']} lines {meta['start_line']}–{meta['end_line']} (reranked)")
        parts.append(f"// {meta['file_path']} (lines {meta['start_line']}–{meta['end_line']})\n{doc.strip()}")

    return "\n\n".join(parts)


def enrich_messages(messages: list) -> tuple[list, dict]:
    """Inject relevant code chunks before the last user message.
    Returns (enriched_messages, metadata_dict)."""
    meta: dict = {
        "repo": None, "raw_query": "", "enriched_message": "",
        "skeleton_injected": False, "chunks_injected": False, "verify_injected": False,
        "task_id": None, "step_type": None, "user_task": None,
    }
    if not messages:
        return messages, meta

    last_user_idx = None
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            last_user_idx = i
            break

    if last_user_idx is None:
        return messages, meta

    user_content = messages[last_user_idx].get("content", "")
    if isinstance(user_content, list):
        user_content = " ".join(
            part.get("text", "") for part in user_content if isinstance(part, dict)
        )

    # Skip enrichment if the user's prompt references a specific file path —
    # Cline will read the file directly via MCP, avoiding format mismatch.
    # Match src/ followed by a filename-like pattern to avoid false positives.
    # Skip enrichment for Cline internal messages — tool results, errors, retries.
    # These start with [ and are not user prompts.
    meta["raw_query"] = user_content
    step_type, task_id, user_task = _detect_step(user_content)
    meta["step_type"] = step_type
    meta["task_id"] = task_id
    meta["user_task"] = user_task

    if user_content.lstrip().startswith("["):
        repo_name = detect_repo(messages)
        if repo_name and _FILE_WRITE_PATTERN.search(user_content):
            _schedule_verify(repo_name)
            print(f"[proxy] file write detected — verification scheduled for {repo_name}")
            if DEP_GRAPH_ENABLED and task_id:
                path_match = _WRITE_PATH_RE.search(user_content)
                if path_match:
                    edited_file = path_match.group(1)
                    impact = _get_impact(repo_name, edited_file)
                    if impact:
                        _pending_impact[task_id] = impact
                        print(f"[dep_graph] impact queued for {edited_file}")
        else:
            print("[proxy] skipping enrichment — Cline internal message")
        meta["enriched_message"] = user_content
        return messages, meta

    match = re.search(r'\b(?:read|edit|update|fix|change|look at|in)\s+src/[\w./\-]+\.\w+', user_content, re.IGNORECASE)
    if match:
        print(f"[proxy] skipping enrichment — explicit file reference: {match.group()}")
        meta["enriched_message"] = user_content
        return messages, meta

    repo_name = detect_repo(messages)
    if repo_name is None:
        print("[proxy] no repo detected in conversation, skipping enrichment")
        meta["enriched_message"] = user_content
        return messages, meta

    meta["repo"] = repo_name

    chunks = hybrid_search(user_content, repo_name)

    with _skeleton_lock:
        skeleton = _repo_skeletons.get(repo_name)

    pending_verify = _pending_verify.pop(repo_name, None)
    pending_impact = _pending_impact.pop(task_id, None) if task_id else None

    if chunks or skeleton or pending_verify or pending_impact:
        parts = []
        if pending_verify:
            parts.append(f"Verification result from previous edit:\n{pending_verify}")
            print(f"[proxy] injecting pending verify result for {repo_name}")
        if pending_impact:
            parts.append(pending_impact)
            print(f"[proxy] injecting dependency impact analysis")
        if skeleton:
            parts.append(f"Codebase structure ({repo_name}):\n{skeleton}")
        if chunks:
            parts.append(f"Relevant code from the project:\n\n{chunks}")
        parts.append(user_content)
        enriched_content = "\n\n---\n\n".join(parts)
        print(f"[proxy] injecting skeleton={skeleton is not None}, chunks={bool(chunks)}, verify={pending_verify is not None} for: {user_content[:80]}")
        messages = list(messages)
        messages[last_user_idx] = {**messages[last_user_idx], "content": enriched_content}
        meta.update({
            "enriched_message": enriched_content,
            "skeleton_injected": skeleton is not None,
            "chunks_injected": bool(chunks),
            "verify_injected": pending_verify is not None,
        })
    else:
        print(f"[proxy] no context found in {repo_name} for: {user_content[:80]}")
        meta["enriched_message"] = user_content

    return messages, meta




@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    import time
    start = time.monotonic()

    body = await request.json()
    if LLM_HAS_THINKING:
        body["enable_thinking"] = False  # disable think blocks — Cline cannot parse them
    body["messages"], enrich_meta = enrich_messages(body.get("messages", []))

    task_id = enrich_meta.get("task_id")

    # If the previous step for this task was a HALT, block immediately
    if task_id and _pending_halt.pop(task_id, False):
        print(f"[proxy] blocking retry after HALT for task {task_id}")
        log_id = _log_prompt(enrich_meta, body["messages"], finish_reason="halt")
        _update_log_response(log_id, _HALT_MSG, "halt", 0, step_type_override="HALT")
        return _halt_json_response()

    stream = body.get("stream", False)

    if stream:
        log_id = _log_prompt(enrich_meta, body["messages"], finish_reason=None)
        response_chunks: list[bytes] = []

        def generate():
            llm_down = False
            stream_exc: Exception | None = None
            try:
                with _http_client.stream(
                    "POST",
                    f"{LLM_URL}/v1/chat/completions",
                    json=body,
                    timeout=120.0,
                ) as r:
                    for chunk in r.iter_bytes():
                        response_chunks.append(chunk)
                        yield chunk
            except httpx.ConnectError:
                llm_down = True
            except Exception as exc:
                stream_exc = exc
                print(f"[proxy] streaming LLM error: {exc}")
            finally:
                latency_ms = int((time.monotonic() - start) * 1000)
                response_text, model, prompt_tokens, completion_tokens = _extract_streaming_response(response_chunks)
                if LLM_HAS_THINKING:
                    response_text = _THINK_RE.sub("", response_text).strip()
                if llm_down:
                    _do_llm_down(log_id, latency_ms)
                elif stream_exc is not None:
                    err_msg = f"[PROXY ERROR] {type(stream_exc).__name__}: {stream_exc}"
                    _update_log_response(log_id, err_msg, "error", latency_ms, step_type_override="ERROR")
                elif not response_text:
                    _do_halt(log_id, latency_ms, task_id)
                else:
                    _update_log_response(log_id, response_text, finish_reason=None,
                                         latency_ms=latency_ms, model=model,
                                         prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
            if llm_down:
                yield from _llm_down_sse_chunks(LLM_URL)

        return StreamingResponse(generate(), media_type="text/event-stream")
    else:
        try:
            response = _http_client.post(f"{LLM_URL}/v1/chat/completions", json=body)
            response.raise_for_status()
            data = response.json()
        except httpx.ConnectError:
            latency_ms = int((time.monotonic() - start) * 1000)
            log_id = _log_prompt(enrich_meta, body["messages"], finish_reason="error")
            _do_llm_down(log_id, latency_ms)
            return _llm_down_json_response()
        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            err_msg = f"[PROXY ERROR] {type(exc).__name__}: {exc}"
            print(f"[proxy] LLM request failed: {err_msg}")
            log_id = _log_prompt(enrich_meta, body["messages"], finish_reason="error")
            _update_log_response(log_id, err_msg, "error", latency_ms, step_type_override="ERROR")
            return _halt_json_response()

        latency_ms = int((time.monotonic() - start) * 1000)
        choices = data.get("choices", [])
        msg = choices[0].get("message", {}) if choices else {}
        finish = choices[0].get("finish_reason") if choices else None
        content = msg.get("content", "")
        tool_calls = msg.get("tool_calls")
        usage = data.get("usage") or {}
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        model = data.get("model")

        if LLM_HAS_THINKING and content:
            content = _THINK_RE.sub("", content).strip()
            if choices:
                data["choices"][0]["message"]["content"] = content

        print(f"[proxy] LLM response: finish={finish} content={bool(content)} tool_calls={bool(tool_calls)} tokens={prompt_tokens}/{completion_tokens}")

        log_id = _log_prompt(enrich_meta, body["messages"], finish_reason=finish)

        if not choices or (not content and not tool_calls):
            _do_halt(log_id, latency_ms, task_id)
            return _halt_json_response()

        _update_log_response(log_id, content, finish, latency_ms, model=model,
                             prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
        return JSONResponse(content=data, status_code=response.status_code)


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
