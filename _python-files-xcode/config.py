"""
Shared configuration for all MCP tools and scripts.
Edit this file to match your own machine setup.
"""

import os

# ===========================================================
# PATHS — change these to match your machine
# ===========================================================

# Root directory where all project repos are checked out
REPO_ROOT = "/Users/roytynan/dev/v4"

# Where ChromaDB persists its vector index
CHROMA_DIR = "/Users/roytynan/dev/mcp-tools/chromadb_data"

# Root directory for locally cloned documentation libraries
DOCS_ROOT = "/Users/roytynan/dev/mcp-tools/docs"

# Path to this tools directory (used by the proxy to call index_repos.py)
TOOLS_DIR = "/Users/roytynan/dev/mcp-tools"

# ===========================================================
# SERVERS
# ===========================================================

# Embedding server — Ollama running locally on Mac (Metal / unified memory)
EMBED_URL = "http://127.0.0.1:11434/api/embeddings"

# LLM inference server — runs on the i9 (used by proxy.py only)
LLM_URL = "http://192.168.178.99:8080"

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
INDEXABLE_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".css", ".json", ".md"}

# Directories to skip during indexing and file watching
EXCLUDED_DIRS = {"node_modules", ".next", "dist", "build", ".git", ".venv", "ios", "android", "Pods", ".expo"}

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
        os.path.join(DOCS_ROOT, "typescript-docs/documentation"),
        os.path.join(DOCS_ROOT, "typescript-docs/tsconfig-reference"),
    ],
    "react-native": [
        os.path.join(DOCS_ROOT, "react-native-docs"),
    ],
    "expo": [
        os.path.join(DOCS_ROOT, "expo-repo/docs/pages"),
    ],
    "skia": [
        os.path.join(DOCS_ROOT, "skia-repo/apps/docs/docs"),
    ],
    "webgl": [
        os.path.join(DOCS_ROOT, "webgl-fundamentals/webgl/lessons"),
    ],
    "glsl": [
        os.path.join(DOCS_ROOT, "book-of-shaders"),
    ],
    "webgl2-types": [
        os.path.join(DOCS_ROOT, "definitely-typed/types/webgl2"),
    ],
}

# Derived — React Native docs path used by server.py for ripgrep search
REACT_DOCS = os.path.join(DOCS_ROOT, "react-native-docs")
