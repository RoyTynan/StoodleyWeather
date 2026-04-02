"""
Indexes third-party documentation into ChromaDB for semantic search.
Run manually after updating any docs package:
    python /mnt/storage/mcp-tools/index_docs.py
    python /mnt/storage/mcp-tools/index_docs.py --lib nextjs --full
"""
import os
import sys
import json
import hashlib
import argparse
import httpx
import chromadb
from chromadb.config import Settings
from config import (
    CHROMA_DIR, EMBED_URL, DOCS_SOURCES,
    DOCS_EXTENSIONS, DOCS_EXCLUDED_DIRS as EXCLUDED_DIRS,
    DOCS_CHUNK_CHARS as CHUNK_CHARS, DOCS_CHUNK_OVERLAP as CHUNK_OVERLAP,
    DOCS_MANIFEST_PATH as MANIFEST_PATH,
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
            text_chunk = "".join(l for _, l in current_lines)
            chunks.append((start_line, end_line, text_chunk))
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
        text_chunk = "".join(l for _, l in current_lines)
        chunks.append((start_line, end_line, text_chunk))

    return chunks


def embed_texts(texts):
    prefixed = ["search_document: " + t for t in texts]
    try:
        response = httpx.post(
            EMBED_URL,
            json={"model": "nomic-embed-text", "input": prefixed},
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]
    except httpx.ConnectError:
        print("ERROR: Embedding server not reachable. Is llama-embed.service running?", file=sys.stderr)
        sys.exit(1)


def index_lib(lib_name, full=False):
    sources = DOCS_SOURCES.get(lib_name)
    if not sources:
        print(f"Unknown library: {lib_name}. Available: {list(DOCS_SOURCES.keys())}", file=sys.stderr)
        return

    client = get_chroma_client()
    collection_name = f"docs_{lib_name}"
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    manifest = load_manifest()
    lib_manifest = manifest.get(lib_name, {})
    total_chunks = 0

    # Expand any directories into individual files
    expanded = []
    for entry in sources:
        if os.path.isdir(entry):
            for root, dirs, files in os.walk(entry):
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
                for fname in files:
                    if os.path.splitext(fname)[1] in DOCS_EXTENSIONS or os.path.splitext(fname)[1] == "":
                        expanded.append(os.path.join(root, fname))
        elif os.path.isfile(entry):
            expanded.append(entry)
        else:
            print(f"  Missing: {entry}", file=sys.stderr)

    print(f"  Found {len(expanded)} files to check.")

    for file_path in expanded:
        if not os.path.exists(file_path):
            print(f"  Missing: {file_path}", file=sys.stderr)
            continue

        file_hash = hash_file(file_path)
        rel = os.path.basename(file_path)

        if not full and lib_manifest.get(file_path) == file_hash:
            print(f"  Unchanged: {rel}")
            continue

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if not content.strip():
            continue

        # Remove old chunks for this file
        try:
            collection.delete(where={"file_path": file_path})
        except Exception:
            pass

        chunks = chunk_text(content)
        if not chunks:
            continue

        # Embed in batches; fall back to single chunks if a batch fails
        batch_size = 4
        all_embeddings = []
        for i in range(0, len(chunks), batch_size):
            batch = [c[2] for c in chunks[i:i + batch_size]]
            try:
                all_embeddings.extend(embed_texts(batch))
            except Exception:
                # Fall back to one chunk at a time
                for j, single in enumerate(batch):
                    try:
                        all_embeddings.extend(embed_texts([single]))
                    except Exception as e:
                        print(f"\n  Skipping chunk {i+j} (too large): {str(e)[:60]}")
                        all_embeddings.append([0.0] * 768)  # placeholder
            print(f"  Embedding {rel}: {min(i + batch_size, len(chunks))}/{len(chunks)} chunks...", end="\r")

        print()
        ids = [f"{lib_name}::{file_path}::{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "lib": lib_name,
                "file_path": file_path,
                "filename": os.path.basename(file_path),
                "start_line": chunks[i][0],
                "end_line": chunks[i][1],
                "chunk_index": i,
            }
            for i in range(len(chunks))
        ]
        texts = [c[2] for c in chunks]

        collection.upsert(ids=ids, embeddings=all_embeddings, documents=texts, metadatas=metadatas)
        lib_manifest[file_path] = file_hash
        total_chunks += len(chunks)
        # Save after each file so progress is preserved on failure
        manifest[lib_name] = lib_manifest
        save_manifest(manifest)
        print(f"  Indexed {rel} ({len(chunks)} chunks)")
    print(f"Done. {total_chunks} chunks indexed for {lib_name}.")


def main():
    parser = argparse.ArgumentParser(description="Index documentation for semantic search.")
    parser.add_argument("--full", action="store_true", help="Re-index regardless of file changes.")
    parser.add_argument("--lib", default=None, help=f"Index a specific library. Options: {list(DOCS_SOURCES.keys())}")
    args = parser.parse_args()

    libs = [args.lib] if args.lib else list(DOCS_SOURCES.keys())
    for lib in libs:
        print(f"\nIndexing {lib}...")
        index_lib(lib, full=args.full)


if __name__ == "__main__":
    main()
