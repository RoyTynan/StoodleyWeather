import re
import httpx
import chromadb
from chromadb.config import Settings
from mcp.server.fastmcp import FastMCP
from config import CHROMA_DIR, EMBED_URL

mcp = FastMCP("docs-engine")

SCORE_THRESHOLD = 0.75

# Maps keyword aliases to collection names
LIBRARY_ALIASES = {
    "typescript": "docs_typescript",
    "ts": "docs_typescript",
    "nextjs": "docs_nextjs",
    "next": "docs_nextjs",
    "react": "docs_react",
    "cesium": "docs_cesium",
    "cesiumjs": "docs_cesium",
}

ALL_COLLECTIONS = list(dict.fromkeys(LIBRARY_ALIASES.values()))


def _embed(query: str):
    response = httpx.post(
        EMBED_URL,
        json={"model": "nomic-embed-text", "input": f"search_query: {query}"},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def _search_collection(collection_name: str, vector: list, n_results: int):
    """Returns list of (score, doc, meta) or empty list if collection missing."""
    try:
        client = chromadb.PersistentClient(
            path=CHROMA_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
        collection = client.get_collection(collection_name)
    except Exception:
        return []
    results = collection.query(query_embeddings=[vector], n_results=n_results)
    hits = []
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        hits.append((round(1 - dist, 3), doc, meta))
    return hits


def _format_hits(hits: list) -> str:
    output = []
    for i, (score, doc, meta) in enumerate(hits, 1):
        output.append(
            f"[{i}] {meta['filename']} (lines {meta['start_line']}–{meta['end_line']}, score: {score})\n"
            f"---\n{doc.strip()}"
        )
    return "\n\n".join(output)


def _parse_prompt(prompt: str):
    """
    Extract target library and search query from a natural-language prompt.
    Patterns: "search cesium for X", "search typescript for X", "search docs for X"
    Falls back to (None, full prompt) if no library is named.
    """
    match = re.match(
        r"search\s+(?:the\s+)?(\w+)\s+(?:docs?\s+)?for\s+(.+)",
        prompt.strip(),
        re.IGNORECASE,
    )
    if match:
        lib_token = match.group(1).lower()
        query = match.group(2).strip()
        if lib_token in ("docs", "all", "documentation"):
            return None, query
        collection = LIBRARY_ALIASES.get(lib_token)
        return collection, query
    return None, prompt.strip()


@mcp.tool()
def search_docs(query: str, n_results: int = 8, repo_name: str = "", task_progress: str = "") -> str:
    """Search indexed documentation libraries using natural language.

    Understands targeted queries:
      "search cesium for camera controls"
      "search typescript for conditional types"
      "search nextjs for ISR"

    Or searches all libraries when no target is named:
      "search docs for routing"
      "what is a viewer"

    Only returns results above a relevance threshold — will not hallucinate.
    """
    collection_name, actual_query = _parse_prompt(query)

    try:
        vector = _embed(actual_query)
    except httpx.ConnectError:
        return "Embedding server not available. Run: sudo systemctl start llama-embed"
    except Exception as e:
        return f"Embedding error: {str(e)}"

    if collection_name:
        # Targeted search — return results as-is (user knows what they asked for)
        hits = _search_collection(collection_name, vector, n_results)
        if not hits:
            return f"Collection '{collection_name}' not found or not indexed yet."
        return _format_hits(hits)
    else:
        # Search all — only return hits above threshold to avoid hallucination
        all_hits = []
        for col in ALL_COLLECTIONS:
            all_hits.extend(_search_collection(col, vector, n_results))

        filtered = [h for h in all_hits if h[0] >= SCORE_THRESHOLD]
        if not filtered:
            return "No relevant documentation found."

        filtered.sort(key=lambda h: h[0], reverse=True)
        return _format_hits(filtered[:n_results])


@mcp.tool()
def search_typescript_docs(query: str, n_results: int = 8, repo_name: str = "", task_progress: str = "") -> str:
    """Semantic search over TypeScript documentation and handbook.
    Find type system features, compiler options and language reference."""
    try:
        vector = _embed(query)
    except httpx.ConnectError:
        return "Embedding server not available. Run: sudo systemctl start llama-embed"
    except Exception as e:
        return f"Embedding error: {str(e)}"
    hits = _search_collection("docs_typescript", vector, n_results)
    if not hits:
        return "TypeScript docs index not found. Run: python index_docs.py --lib typescript"
    return _format_hits(hits)


@mcp.tool()
def search_nextjs_docs(query: str, n_results: int = 8, repo_name: str = "", task_progress: str = "") -> str:
    """Semantic search over Next.js documentation.
    Find routing, data fetching, rendering, API routes and configuration."""
    try:
        vector = _embed(query)
    except httpx.ConnectError:
        return "Embedding server not available. Run: sudo systemctl start llama-embed"
    except Exception as e:
        return f"Embedding error: {str(e)}"
    hits = _search_collection("docs_nextjs", vector, n_results)
    if not hits:
        return "Next.js docs index not found. Run: python index_docs.py --lib nextjs"
    return _format_hits(hits)


@mcp.tool()
def search_cesium_docs(query: str, n_results: int = 8, repo_name: str = "", task_progress: str = "") -> str:
    """Semantic search over CesiumJS API documentation and type declarations.
    Find classes, methods, properties and usage for 3D globe, terrain, tiles, entities and cameras."""
    try:
        vector = _embed(query)
    except httpx.ConnectError:
        return "Embedding server not available. Run: sudo systemctl start llama-embed"
    except Exception as e:
        return f"Embedding error: {str(e)}"
    hits = _search_collection("docs_cesium", vector, n_results)
    if not hits:
        return "Cesium docs index not found. Run: python index_docs.py --lib cesium"
    return _format_hits(hits)


if __name__ == "__main__":
    mcp.run()
