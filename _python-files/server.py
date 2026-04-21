import os
import subprocess
import httpx
import chromadb
from chromadb.config import Settings
from mcp.server.fastmcp import FastMCP
from functools import lru_cache
from config import REPO_ROOT, CHROMA_DIR, EMBED_URL, EMBED_QUERY_PREFIX, REACT_DOCS
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
def list_repos(task_progress: str = "") -> str:
    """Lists all repositories currently available."""
    try:
        repos = [d for d in os.listdir(REPO_ROOT) if os.path.isdir(os.path.join(REPO_ROOT, d))]
        return "\n".join(repos) if repos else "No repositories found."
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def read_repo_file(repo_name: str, relative_path: str, task_progress: str = "") -> str:
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
def search_official_docs(query: str, task_progress: str = "") -> str:
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
def read_doc_page(full_path: str, task_progress: str = "") -> str:
    """Reads a specific documentation file found via search_official_docs."""
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading doc: {str(e)}"


@mcp.tool()
def semantic_search(query: str, repo_name: str, n_results: int = 3, task_progress: str = "") -> str:
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
def verify_project(repo_name: str, task_progress: str = "") -> str:
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


if __name__ == "__main__":
    mcp.run()
