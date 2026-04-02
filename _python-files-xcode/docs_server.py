import httpx
import chromadb
from chromadb.config import Settings
from mcp.server.fastmcp import FastMCP
from config import CHROMA_DIR, EMBED_URL

mcp = FastMCP("docs-engine")


def _embed(query: str):
    response = httpx.post(
        EMBED_URL,
        json={"model": "nomic-embed-text", "input": f"search_query: {query}"},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def _search(collection_name: str, query: str, n_results: int, error_msg: str) -> str:
    try:
        vector = _embed(query)
    except httpx.ConnectError:
        return "Embedding server not available. Run: sudo systemctl start llama-embed"
    except Exception as e:
        return f"Embedding error: {str(e)}"

    try:
        client = chromadb.PersistentClient(
            path=CHROMA_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
        collection = client.get_collection(collection_name)
    except Exception:
        return error_msg

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
            f"[{i}] {meta['filename']} (lines {meta['start_line']}–{meta['end_line']}, score: {score})\n"
            f"---\n{doc.strip()}"
        )
    return "\n\n".join(output)


@mcp.tool()
def search_typescript_docs(query: str, n_results: int = 8, repo_name: str = "", task_progress: str = "") -> str:
    """Semantic search over TypeScript documentation and handbook.
    Find type system features, compiler options and language reference."""
    return _search("docs_typescript", query, n_results,
                   "TypeScript docs index not found. Run: python /mnt/storage/mcp-tools/index_docs.py --lib typescript")


@mcp.tool()
def search_nextjs_docs(query: str, n_results: int = 8, repo_name: str = "", task_progress: str = "") -> str:
    """Semantic search over Next.js documentation.
    Find routing, data fetching, rendering, API routes and configuration by describing what you need."""
    return _search("docs_nextjs", query, n_results,
                   "Next.js docs index not found. Run: python /mnt/storage/mcp-tools/index_docs.py --lib nextjs")


if __name__ == "__main__":
    mcp.run()
