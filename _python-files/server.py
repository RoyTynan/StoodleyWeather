import os
import sqlite3
import subprocess
import httpx
import chromadb
from chromadb.config import Settings
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP
from functools import lru_cache
from config import REPO_ROOT, CHROMA_DIR, EMBED_URL, EMBED_QUERY_PREFIX, REACT_DOCS, PROMPT_LOG_DB
from verify import verify

mcp = FastMCP("Context Engine")

# Module-level singletons — initialised once at startup
_http_client = httpx.Client(timeout=30.0)
_chroma_client = chromadb.PersistentClient(
    path=CHROMA_DIR,
    settings=Settings(anonymized_telemetry=False),
)


@lru_cache(maxsize=256)
def _get_embedding(query: str) -> list:
    """Embed a query string, cached by query text."""
    response = _http_client.post(
        EMBED_URL,
        json={"model": "bge-m3", "input": f"{EMBED_QUERY_PREFIX}{query}"},
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


@mcp.tool()
def list_repos() -> str:
    """Lists all repositories currently available."""
    try:
        repos = [d for d in os.listdir(REPO_ROOT) if os.path.isdir(os.path.join(REPO_ROOT, d))]
        return "\n".join(repos) if repos else "No repositories found."
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def read_repo_file(repo_name: str, relative_path: str) -> str:
    """Reads a file from your project repo (limited to 500 lines)."""
    full_path = os.path.join(REPO_ROOT, repo_name, relative_path)
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if len(lines) > 500:
                return "".join(lines[:500]) + "\n\n... [File truncated] ..."
            return "".join(lines)
    except Exception as e:
        return f"Read error: {str(e)}"


@mcp.tool()
def search_official_docs(query: str) -> str:
    """Search official React documentation."""
    target = REACT_DOCS
    if not os.path.exists(target):
        return f"Docs path {target} not found."
    cmd = ["rg", "-i", "-C", "2", "-m", "15", "--max-columns", "150", query, target]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.stdout:
        return result.stdout
    if result.stderr:
        return f"rg error: {result.stderr.strip()}"
    return f"No documentation found for '{query}'."


@mcp.tool()
def read_doc_page(full_path: str) -> str:
    """Reads a specific documentation file found via search_official_docs."""
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading doc: {str(e)}"


@mcp.tool()
def semantic_search(query: str, repo_name: str, n_results: int = 3) -> str:
    """
    Semantic vector search over a repository using natural language.
    Use when searching by concept rather than exact keyword.
    Returns file path, line range, and source snippet.
    """
    repo_path = os.path.join(REPO_ROOT, repo_name)
    if not os.path.isdir(repo_path):
        return f"Error: repo '{repo_name}' not found under {REPO_ROOT}."

    try:
        vector = _get_embedding(query)
    except httpx.ConnectError:
        return "Embedding server not available. Run: sudo systemctl start llama-embed"
    except Exception as e:
        return f"Embedding error: {str(e)}"

    try:
        collection = _chroma_client.get_collection(f"repo_{repo_name}")
    except Exception:
        return f"Index not found for '{repo_name}'. Run: python /mnt/storage/mcp-tools/index_repos.py"

    results = collection.query(query_embeddings=[vector], n_results=n_results)
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    if not docs:
        return "No results found."

    output = []
    for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances), 1):
        score = round(1 - dist, 3)
        output.append(
            f"[{i}] {meta['file_path']} (lines {meta['start_line']}–{meta['end_line']}, score: {score})\n"
            f"---\n{doc.strip()}"
        )
    return "\n\n".join(output)


@mcp.tool()
def verify_project(repo_name: str) -> str:
    """
    Auto-detects the project type and runs appropriate verification checks.
    Supports TypeScript, React, React Native, and C++ (CMake/Make).
    Call this after making code changes to confirm they are correct before finishing.
    Returns pass/fail status and any compiler or linter errors.
    """
    repo_path = os.path.join(REPO_ROOT, repo_name)
    if not os.path.isdir(repo_path):
        return f"Error: repo '{repo_name}' not found under {REPO_ROOT}."
    try:
        result = verify(repo_path, repo_name)
        return result.summary()
    except Exception as e:
        return f"Verification error: {e}"


@mcp.tool()
def compact_context() -> str:
    """Report how much context the proxy is pruning per request for the current task."""
    try:
        conn = sqlite3.connect(PROMPT_LOG_DB)
        row = conn.execute(
            "SELECT task_id FROM prompts WHERE task_id IS NOT NULL ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            conn.close()
            return "No active task found in the prompt log."
        task_id = row[0]

        rows = conn.execute(
            "SELECT chars_pruned, prompt_tokens, step_type FROM prompts WHERE task_id = ? ORDER BY id",
            (task_id,)
        ).fetchall()
        summary_count = conn.execute(
            "SELECT COUNT(*) FROM message_summaries WHERE task_id = ?", (task_id,)
        ).fetchone()[0]
        conn.close()
    except Exception as e:
        return f"Could not read prompt log: {e}"

    if not rows:
        return "No steps found for current task."

    total_steps = len(rows)
    latest_pruned = rows[-1][0] or 0
    latest_tokens = rows[-1][1] or 0
    steps_with_pruning = sum(1 for r in rows if (r[0] or 0) > 0)

    if latest_pruned == 0:
        output = (
            f"Context pruning report: no pruning active on the most recent request.\n\n"
            f"Task has {total_steps} step(s). The proxy strips code blocks from messages older "
            f"than the last 4 — this task may be too short to trigger pruning yet."
        )
    else:
        saved_tokens = latest_pruned // 4
        orig_chars_est = latest_pruned + (latest_tokens * 4)
        pct = int(latest_pruned / orig_chars_est * 100) if orig_chars_est else 0

        output = (
            f"## Context Pruning Report\n\n"
            f"**Layer 1 — regex pruning:** active — code blocks stripped from messages older than last 4\n"
            f"**Savings on last request:** ~{latest_pruned:,} chars (~{saved_tokens:,} tokens, {pct}% of context)\n"
            f"**Steps with pruning active:** {steps_with_pruning} of {total_steps}\n"
            f"**Layer 2 — LLM summaries:** {summary_count} message(s) summarised for this task\n"
            f"**Current prompt size:** ~{latest_tokens:,} tokens\n\n"
            f"Pruning runs automatically on every request — no action needed."
        )

    try:
        with sqlite3.connect(PROMPT_LOG_DB) as log_conn:
            log_conn.execute(
                """INSERT INTO prompts (timestamp, task_id, step_type, raw_query, response_text, prompt_tokens)
                   VALUES (?, ?, 'COMPACT', 'compact_context', ?, ?)""",
                (datetime.now(timezone.utc).isoformat(), task_id, output, latest_tokens),
            )
    except Exception:
        pass

    return output


if __name__ == "__main__":
    mcp.run()
