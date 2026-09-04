"""FastEmbed model loading and text-vector generation."""

from functools import lru_cache

from fastembed import TextEmbedding

from ..core.settings import MODEL_CACHE_DIR, MODEL_NAME, VECTOR_SIZE
from ..metrics import EMBEDDING_DURATION


@lru_cache(maxsize=1)
def get_embedding_model() -> TextEmbedding:
    """Load and cache the configured text-embedding model."""
    return TextEmbedding(
        model_name=MODEL_NAME,
        cache_dir=MODEL_CACHE_DIR,
    )


def _truncate_vector(vector: list[float]) -> list[float]:
    """Return a vector matching the dimension configured for Qdrant."""
    if len(vector) < VECTOR_SIZE:
        raise ValueError(
            "Embedding model produced "
            f"{len(vector)} dimensions, fewer than VECTOR_SIZE={VECTOR_SIZE}"
        )
    return vector[:VECTOR_SIZE]


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Generate an embedding vector for each document in ``texts``."""
    model = get_embedding_model()
    with EMBEDDING_DURATION.labels(operation="documents").time():
        return [
            _truncate_vector(vector.tolist())
            for vector in model.embed(texts)
        ]


def embed_query(text: str) -> list[float]:
    """Generate an embedding vector for a single search query."""
    model = get_embedding_model()
    with EMBEDDING_DURATION.labels(operation="query").time():
        return _truncate_vector(next(model.embed([text])).tolist())
