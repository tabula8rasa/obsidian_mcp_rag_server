"""Environment-backed configuration values for the RAG API."""

import os
from pathlib import Path

# URL used by the API to connect to the Qdrant vector database.
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")

# Name of the Qdrant collection that stores embedded vault chunks.
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "obsidian_chunks")

# FastEmbed model used to convert note content and queries into vectors.
MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

# Number of dimensions produced by MODEL_NAME; must match the model output.
VECTOR_SIZE = int(os.getenv("VECTOR_SIZE", "384"))

# Persistent directory where downloaded embedding model files are cached.
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "/models")

# Read-only root directory containing the mounted Obsidian vault.
VAULT_PATH = os.getenv("VAULT_PATH", "/vault")

# Persistent directory used to store application synchronization state.
STATE_PATH = os.getenv("STATE_PATH", "/state")

# File that records the Git commit currently represented by the vector index.
LAST_INDEXED_COMMIT_FILE = os.getenv(
    "LAST_INDEXED_COMMIT_FILE",
    str(Path(STATE_PATH) / "last_indexed_commit"),
)

# Maximum number of characters allowed in an indexed text chunk.
MAX_CHUNK_CHARS = int(os.getenv("MAX_CHUNK_CHARS", "1800"))

# Minimum characters required for a heading-free chunk to be indexed.
MIN_CHUNK_CHARS = int(os.getenv("MIN_CHUNK_CHARS", "1"))
