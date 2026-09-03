from functools import lru_cache

from fastembed import TextEmbedding

from .settings import MODEL_CACHE_DIR, MODEL_NAME


@lru_cache(maxsize=1)
def get_embedding_model() -> TextEmbedding:
    """Load and cache the configured text-embedding model."""
    return TextEmbedding(
        model_name=MODEL_NAME,
        cache_dir=MODEL_CACHE_DIR,
    )


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Generate an embedding vector for each document in ``texts``."""
    model = get_embedding_model()
    return [vector.tolist() for vector in model.embed(texts)]


def embed_query(text: str) -> list[float]:
    """Generate an embedding vector for a single search query."""
    model = get_embedding_model()
    return next(model.embed([text])).tolist()
