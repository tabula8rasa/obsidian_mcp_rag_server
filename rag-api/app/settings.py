import os

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "obsidian_chunks")

MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "/models")

VAULT_PATH = os.getenv("VAULT_PATH", "/vault")

MAX_CHUNK_CHARS = int(os.getenv("MAX_CHUNK_CHARS", "1800"))
MIN_CHUNK_CHARS = int(os.getenv("MIN_CHUNK_CHARS", "120"))
