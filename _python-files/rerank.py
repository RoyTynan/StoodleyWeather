"""
Cross-encoder reranker — second-pass scoring of RAG candidates.
Loaded lazily on first call so proxy startup is unaffected.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2
  ~90MB, CPU-only, ~100ms for 15 chunks.
"""

from sentence_transformers import CrossEncoder

_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_model: CrossEncoder | None = None


def _get_model() -> CrossEncoder:
    global _model
    if _model is None:
        print(f"[rerank] loading {_MODEL_NAME}...")
        _model = CrossEncoder(_MODEL_NAME)
        print("[rerank] model ready")
    return _model


def rerank(query: str, chunks: list[tuple[str, dict]], top_n: int) -> list[tuple[str, dict]]:
    """
    Re-score chunks against query using a cross-encoder and return the top_n.
    Falls back to the original order if the model fails to load.
    """
    if not chunks:
        return chunks
    try:
        model = _get_model()
        pairs = [(query, doc) for doc, _ in chunks]
        scores = model.predict(pairs)
        ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in ranked[:top_n]]
    except Exception as e:
        print(f"[rerank] error — falling back to RRF order: {e}")
        return chunks[:top_n]
