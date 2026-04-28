import sqlite3
import os
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Context Bridge")

DB_PATH = os.path.join(os.path.dirname(__file__), "context_bridge.db")


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contexts (
            key   TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


@mcp.tool()
def save_context(query: str, repo_name: str = "default", task_progress: str = "") -> str:
    """
    Save context or a crafted prompt to the bridge database.
    The content is stored under the repo_name key and can be retrieved by any connected agent.
    Use this to hand off a spec, context dump, or finished Cline prompt between agents.
    """
    key = repo_name or "default"
    now = datetime.now(timezone.utc).isoformat()
    with _db() as conn:
        conn.execute(
            "INSERT INTO contexts (key, content, updated_at) VALUES (?, ?, ?) "            "ON CONFLICT(key) DO UPDATE SET content=excluded.content, updated_at=excluded.updated_at",
            (key, query, now),
        )
    return f"Saved context under key '{key}' at {now}"


@mcp.tool()
def get_context(query: str = "", repo_name: str = "default", task_progress: str = "") -> str:
    """
    Retrieve context or a prompt from the bridge database by key (repo_name).
    Use this to read a spec or finished Cline prompt that another agent has saved.
    """
    key = repo_name or "default"
    with _db() as conn:
        row = conn.execute(
            "SELECT content, updated_at FROM contexts WHERE key = ?", (key,)
        ).fetchone()
    if row is None:
        return f"No context found for key '{key}'. Use save_context to store something first."
    content, updated_at = row
    return content


@mcp.tool()
def list_contexts(query: str = "", repo_name: str = "", task_progress: str = "") -> str:
    """
    List all context keys currently stored in the bridge database, with timestamps.
    """
    with _db() as conn:
        rows = conn.execute(
            "SELECT key, updated_at FROM contexts ORDER BY updated_at DESC"
        ).fetchall()
    if not rows:
        return "No contexts stored yet."
    return "\n".join(f"{key}  (updated {updated_at})" for key, updated_at in rows)


if __name__ == "__main__":
    mcp.run()
