"""
Shared configuration for all MCP tools and scripts.
Edit this file to match your own machine setup.
"""

import os

# ===========================================================
# PATHS — change these to match your machine
# ===========================================================

# Root directory where all project repos are checked out
REPO_ROOT = "/home/roy/mcp-context/repos"

# Where ChromaDB persists its vector index
CHROMA_DIR = "/mnt/storage/chromadb"

# Root directory for locally cloned documentation libraries
DOCS_ROOT = "/mnt/storage/docs/frameworks"

# Path to this tools directory (used by the proxy to call index_repos.py)
TOOLS_DIR = "/mnt/storage/mcp-tools"

# ===========================================================
# SERVERS
# ===========================================================

# Embedding server — runs on the i7 via llama-embed.service
EMBED_URL = "http://127.0.0.1:11435/v1/embeddings"

# LLM inference server — runs on the i9 (used by proxy.py only)
LLM_URL = "http://192.168.178.99:8080"

# ===========================================================
# PROXY (proxy.py)
# ===========================================================

# Number of ChromaDB chunks to inject into each enriched prompt
N_CONTEXT_CHUNKS = 5

# Derived — do not edit
INDEX_SCRIPT = os.path.join(TOOLS_DIR, "index_repos.py")
VENV_PYTHON = os.path.join(TOOLS_DIR, ".venv/bin/python")

# ===========================================================
# FILE INDEXING (index_repos.py, proxy.py)
# ===========================================================

# File types to index into ChromaDB
INDEXABLE_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".css", ".json"}

# Directories to skip during indexing and file watching
EXCLUDED_DIRS = {"node_modules", ".next", "dist", "build", ".git", ".venv"}

# Specific files to skip
EXCLUDED_FILES = {"package-lock.json"}

# Chunk size and overlap when splitting repo source files into embeddings
CHUNK_CHARS = 600
CHUNK_OVERLAP = 120

# Chunk size and overlap for documentation libraries (kept smaller to stay
# within llama-server batch-size limit)
DOCS_CHUNK_CHARS = 800
DOCS_CHUNK_OVERLAP = 120

# File types to index for documentation libraries
DOCS_EXTENSIONS = {".md", ".mdx", ".txt", ".d.ts", ".ts", ".tsx", ".js", ".jsx", ".json"}

# Directories to skip when walking documentation sources
DOCS_EXCLUDED_DIRS = {"tr1", "ext", "debug", "backward", "decimal", "profile"}

# ===========================================================
# MANIFEST PATHS (index_repos.py, index_docs.py)
# ===========================================================

# Derived — do not edit
REPO_MANIFEST_PATH = os.path.join(CHROMA_DIR, "index_manifest.json")
DOCS_MANIFEST_PATH = os.path.join(CHROMA_DIR, "docs_manifest.json")

# ===========================================================
# DOCUMENTATION SOURCES (index_docs.py)
# Update these paths to where you downloaded each library.
# Remove libraries you don't need, add your own if required.
# ===========================================================

DOCS_SOURCES = {
    "typescript": [
        os.path.join(DOCS_ROOT, "typescript-docs/packages/documentation/copy/en"),
        os.path.join(DOCS_ROOT, "typescript-docs/packages/tsconfig-reference"),
    ],
    "nextjs": [
        os.path.join(DOCS_ROOT, "nextjs-docs/docs"),
    ],
    "react": [
        os.path.join(DOCS_ROOT, "react-docs/src/content"),
    ],
}

# Derived — React docs path used by server.py for ripgrep search
REACT_DOCS = os.path.join(DOCS_ROOT, "react-docs/src/content")
