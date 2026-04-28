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

# Embedding server — runs on the i7 via llama-embed.service (bge-m3-Q8_0)
EMBED_URL = "http://127.0.0.1:11435/v1/embeddings"
EMBED_QUERY_PREFIX = "query: "      # bge-m3 query prefix
EMBED_PASSAGE_PREFIX = "passage: "  # bge-m3 document prefix

# LLM inference server — runs on the i9 (used by proxy.py only)
LLM_URL = "http://192.168.178.99:8080"

# Set to True for models that output <think>...</think> blocks (Qwen3, DeepSeek-R1).
# The proxy strips think blocks before returning to Cline and disables them at the
# model level via enable_thinking=False in the request body.
LLM_HAS_THINKING = True

# ===========================================================
# PROXY (proxy.py)
# ===========================================================

# Number of ChromaDB chunks to inject into each enriched prompt
N_CONTEXT_CHUNKS = 5

# Maximum number of files to include in the skeleton codebase map
# Keeps the preamble compact on larger repos
SKELETON_MAX_FILES = 60

# Derived — do not edit
INDEX_SCRIPT = os.path.join(TOOLS_DIR, "index_repos.py")
VENV_PYTHON = os.path.join(TOOLS_DIR, ".venv/bin/python")

# ===========================================================
# FILE INDEXING (index_repos.py, proxy.py)
# ===========================================================

# File types to index into ChromaDB
INDEXABLE_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".css", ".json", ".md", ".py", ".cpp", ".h", ".c"}

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

# ===========================================================
# DEPENDENCY GRAPH (index_repos.py, proxy.py)
# ===========================================================

# Enable import-edge analysis — injects impact warnings when an edited file
# is imported by other files in the repo
DEP_GRAPH_ENABLED = True

# Maximum number of dependent files to report per edit
MAX_IMPACT_FILES = 5

# Derived — do not edit
DEP_GRAPH_DB = os.path.join(CHROMA_DIR, "dep_graph.db")

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
