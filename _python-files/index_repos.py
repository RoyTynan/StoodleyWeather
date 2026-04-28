import os
import re
import sys
import json
import sqlite3
import hashlib
import argparse
import fnmatch
import httpx
import chromadb
from chromadb.config import Settings
from config import (
    REPO_ROOT, CHROMA_DIR, EMBED_URL, EMBED_PASSAGE_PREFIX,
    INDEXABLE_EXTENSIONS, EXCLUDED_DIRS, EXCLUDED_FILES,
    CHUNK_CHARS, CHUNK_OVERLAP, REPO_MANIFEST_PATH as MANIFEST_PATH,
    DEP_GRAPH_ENABLED, DEP_GRAPH_DB,
)


def get_chroma_client():
    os.makedirs(CHROMA_DIR, exist_ok=True)
    return chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False),
    )


def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r") as f:
            return json.load(f)
    return {}


def save_manifest(manifest):
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)


def hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def chunk_text(text, chunk_chars=CHUNK_CHARS, overlap=CHUNK_OVERLAP):
    lines = text.splitlines(keepends=True)
    chunks = []
    current_chars = 0
    current_lines = []
    start_line = 1
    line_num = 1

    for line in lines:
        current_lines.append((line_num, line))
        current_chars += len(line)
        if current_chars >= chunk_chars:
            end_line = line_num
            chunk_text = "".join(l for _, l in current_lines)
            chunks.append((start_line, end_line, chunk_text))
            # overlap: keep last N chars worth of lines
            overlap_lines = []
            overlap_chars = 0
            for ln, l in reversed(current_lines):
                overlap_chars += len(l)
                overlap_lines.insert(0, (ln, l))
                if overlap_chars >= overlap:
                    break
            current_lines = overlap_lines
            current_chars = overlap_chars
            start_line = current_lines[0][0] if current_lines else line_num + 1
        line_num += 1

    if current_lines:
        end_line = current_lines[-1][0]
        chunk_text = "".join(l for _, l in current_lines)
        chunks.append((start_line, end_line, chunk_text))

    return chunks


def embed_texts(texts, batch_size=8):
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        batch = [EMBED_PASSAGE_PREFIX + t for t in batch_texts]
        try:
            response = httpx.post(
                EMBED_URL,
                json={"model": "bge-m3", "input": batch},
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            all_embeddings.extend([item["embedding"] for item in data["data"]])
        except httpx.ConnectError:
            print("ERROR: Embedding server not reachable at 11435. Is llama-embed.service running?", file=sys.stderr)
            sys.exit(1)
        except httpx.HTTPStatusError as e:
            if len(batch_texts) == 1:
                # Single chunk failed — log and substitute a zero vector so indexing continues
                print(f"  WARNING: embedding failed for chunk (skipping): {repr(batch_texts[0][:80])}", file=sys.stderr)
                all_embeddings.append([0.0] * 1024)
            else:
                # Batch failed — retry each chunk individually to isolate the bad one
                for single in batch_texts:
                    try:
                        r = httpx.post(
                            EMBED_URL,
                            json={"model": "bge-m3", "input": [EMBED_PASSAGE_PREFIX + single]},
                            timeout=60.0,
                        )
                        r.raise_for_status()
                        all_embeddings.append(r.json()["data"][0]["embedding"])
                    except Exception:
                        print(f"  WARNING: embedding failed for chunk (skipping): {repr(single[:80])}", file=sys.stderr)
                        all_embeddings.append([0.0] * 1024)
    return all_embeddings


def load_chromaignore(repo_path: str) -> list[str]:
    """Load patterns from .chromaignore in the repo root. One pattern per line, # for comments."""
    ignore_path = os.path.join(repo_path, ".chromaignore")
    if not os.path.exists(ignore_path):
        return []
    with open(ignore_path) as f:
        return [
            line.strip() for line in f
            if line.strip() and not line.strip().startswith("#")
        ]


def is_ignored(rel_path: str, patterns: list[str]) -> bool:
    rel_path = rel_path.replace(os.sep, "/")
    for pattern in patterns:
        p = pattern.rstrip("/").replace("**", "*")
        if fnmatch.fnmatch(rel_path, p):
            return True
        if fnmatch.fnmatch(rel_path, p + "/*"):
            return True
        parts = rel_path.split("/")
        for i in range(len(parts)):
            if fnmatch.fnmatch("/".join(parts[:i + 1]), p):
                return True
    return False


def iter_repo_files(repo_path):
    ignore_patterns = load_chromaignore(repo_path)
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for fname in files:
            if fname in EXCLUDED_FILES:
                continue
            ext = os.path.splitext(fname)[1]
            if ext not in INDEXABLE_EXTENSIONS:
                continue
            abs_path = os.path.join(root, fname)
            rel_path = os.path.relpath(abs_path, repo_path)
            if ignore_patterns and is_ignored(rel_path, ignore_patterns):
                continue
            yield abs_path


_IMPORT_RE = re.compile(
    r"""(?:import\s+.*?\s+from\s+|import\s*\(\s*|require\s*\(\s*)['"](\.[^'"]+)['"]""",
    re.DOTALL,
)

_DEP_GRAPH_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".py"}


def _resolve_import(import_str: str, file_rel: str, repo_path: str) -> str | None:
    """Resolve a relative import path to a repo-relative file path, or None."""
    if not import_str.startswith("."):
        return None
    file_dir = os.path.dirname(os.path.join(repo_path, file_rel))
    resolved = os.path.normpath(os.path.join(file_dir, import_str))
    rel = os.path.relpath(resolved, repo_path).replace(os.sep, "/")
    if os.path.isfile(resolved):
        return rel
    for ext in (".ts", ".tsx", ".js", ".jsx", ".py"):
        if os.path.isfile(resolved + ext):
            return rel + ext
    for ext in (".ts", ".tsx", ".js", ".jsx"):
        idx = os.path.join(resolved, f"index{ext}")
        if os.path.isfile(idx):
            return os.path.relpath(idx, repo_path).replace(os.sep, "/")
    return None


def build_dep_graph(repo_name: str, repo_path: str, file_content_map: dict):
    """Write import edges for repo_name into dep_graph.db."""
    conn = sqlite3.connect(DEP_GRAPH_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS edges (
            repo         TEXT NOT NULL,
            file         TEXT NOT NULL,
            imports_file TEXT NOT NULL,
            PRIMARY KEY (repo, file, imports_file)
        )
    """)
    conn.execute("DELETE FROM edges WHERE repo = ?", (repo_name,))
    rows = []
    for rel_path, content in file_content_map.items():
        if os.path.splitext(rel_path)[1] not in _DEP_GRAPH_EXTENSIONS:
            continue
        for m in _IMPORT_RE.finditer(content):
            resolved = _resolve_import(m.group(1), rel_path, repo_path)
            if resolved:
                rows.append((repo_name, rel_path, resolved))
    if rows:
        conn.executemany(
            "INSERT OR REPLACE INTO edges (repo, file, imports_file) VALUES (?, ?, ?)",
            rows,
        )
    conn.commit()
    conn.close()
    print(f"[dep_graph] {len(rows)} import edges for {repo_name}")


def index_repo(repo_name, full=False):
    repo_path = os.path.join(REPO_ROOT, repo_name)
    if not os.path.isdir(repo_path):
        print(f"Repo not found: {repo_path}", file=sys.stderr)
        return

    client = get_chroma_client()
    collection_name = f"repo_{repo_name}"
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    manifest = load_manifest()
    repo_manifest = manifest.get(repo_name, {})
    seen_paths = set()
    total_chunks = 0
    file_content_map: dict[str, str] = {}

    all_files = list(iter_repo_files(repo_path))
    print(f"Scanning {len(all_files)} files in {repo_name}...")

    for file_path in all_files:
        rel_path = os.path.relpath(file_path, repo_path)
        seen_paths.add(rel_path)
        file_hash = hash_file(file_path)

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            print(f"  Skip {rel_path}: {e}", file=sys.stderr)
            continue

        file_content_map[rel_path] = content

        if not full and repo_manifest.get(rel_path) == file_hash:
            continue

        if not content.strip():
            continue

        # Remove old chunks for this file
        try:
            collection.delete(where={"file_path": rel_path})
        except Exception:
            pass

        chunks = chunk_text(content)
        if not chunks:
            continue

        texts = [c[2] for c in chunks]
        embeddings = embed_texts(texts)

        ids = [f"{repo_name}::{rel_path}::{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "repo_name": repo_name,
                "file_path": rel_path,
                "start_line": chunks[i][0],
                "end_line": chunks[i][1],
                "file_ext": os.path.splitext(rel_path)[1],
                "chunk_index": i,
            }
            for i in range(len(chunks))
        ]

        collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        repo_manifest[rel_path] = file_hash
        total_chunks += len(chunks)
        print(f"  Indexed {rel_path} ({len(chunks)} chunks)")

    # Remove deleted files from index and manifest
    deleted = set(repo_manifest.keys()) - seen_paths
    for rel_path in deleted:
        try:
            collection.delete(where={"file_path": rel_path})
        except Exception:
            pass
        del repo_manifest[rel_path]
        print(f"  Removed deleted file: {rel_path}")

    manifest[repo_name] = repo_manifest
    save_manifest(manifest)
    print(f"Done. {total_chunks} chunks indexed for {repo_name}.")

    if DEP_GRAPH_ENABLED:
        build_dep_graph(repo_name, repo_path, file_content_map)


def main():
    parser = argparse.ArgumentParser(description="Index repos for semantic search.")
    parser.add_argument("--full", action="store_true", help="Re-index all files regardless of changes.")
    parser.add_argument("--repo", default=None, help="Index a specific repo only.")
    args = parser.parse_args()

    if args.repo:
        repos = [args.repo]
    else:
        repos = [d for d in os.listdir(REPO_ROOT) if os.path.isdir(os.path.join(REPO_ROOT, d))]

    for repo in repos:
        index_repo(repo, full=args.full)


if __name__ == "__main__":
    main()
