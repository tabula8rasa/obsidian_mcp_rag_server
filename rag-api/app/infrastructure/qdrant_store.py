"""Qdrant persistence and vector-search operations."""

from __future__ import annotations

import uuid
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from ..core.settings import COLLECTION_NAME, QDRANT_URL
from ..domain.chunk import Chunk
from .embedding_model import embed_documents, embed_query


EMBEDDING_BATCH_SIZE = 64


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """Create and cache a client for the configured Qdrant instance."""
    return QdrantClient(url=QDRANT_URL)


def _create_collection(vector_size: int) -> None:
    """Create the configured collection with cosine-distance vectors."""
    get_qdrant_client().create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE,
        ),
    )


def _ensure_source_path_index() -> None:
    """Ensure the collection has a keyword index for note source paths."""
    client = get_qdrant_client()
    info = client.get_collection(COLLECTION_NAME)
    if "source_path" in (info.payload_schema or {}):
        return

    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="source_path",
        field_schema=PayloadSchemaType.KEYWORD,
        wait=True,
    )


def ensure_collection(vector_size: int) -> None:
    """Create the collection and required payload index when absent."""
    client = get_qdrant_client()
    if not client.collection_exists(COLLECTION_NAME):
        _create_collection(vector_size)
    _ensure_source_path_index()


def _point_id(chunk: Chunk) -> str:
    """Derive a deterministic UUID from a chunk's source path and position."""
    key = f"{chunk.source_path}:{chunk.chunk_index}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def upsert_chunks(chunks: list[Chunk]) -> int:
    """Embed and upsert chunks in batches, returning the indexed count."""
    client = get_qdrant_client()

    for start in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch = chunks[start:start + EMBEDDING_BATCH_SIZE]
        vectors = embed_documents([chunk.text for chunk in batch])
        points = [
            PointStruct(
                id=_point_id(chunk),
                vector=vector,
                payload={
                    "source_path": chunk.source_path,
                    "note_name": chunk.note_name,
                    "heading": chunk.heading,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                },
            )
            for chunk, vector in zip(batch, vectors, strict=True)
        ]
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
            wait=True,
        )

    return len(chunks)


def delete_note_chunks(source_path: str) -> None:
    """Delete every indexed chunk associated with a source path."""
    get_qdrant_client().delete(
        collection_name=COLLECTION_NAME,
        points_selector=FilterSelector(
            filter=Filter(
                must=[
                    FieldCondition(
                        key="source_path",
                        match=MatchValue(value=source_path),
                    )
                ]
            )
        ),
        wait=True,
    )


def rebuild_index(chunks: list[Chunk], vector_size: int) -> int:
    """Recreate the collection and populate it with the supplied chunks."""
    client = get_qdrant_client()
    client.delete_collection(COLLECTION_NAME)
    _create_collection(vector_size)
    _ensure_source_path_index()
    return upsert_chunks(chunks)


def search_chunks(query: str, limit: int) -> list[dict]:
    """Return up to ``limit`` chunks nearest to the embedded query."""
    query_vector = embed_query(query)
    response = get_qdrant_client().query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=limit,
        with_payload=True,
    )

    return [
        {
            "id": point.id,
            "score": point.score,
            "source_path": point.payload.get("source_path"),
            "note_name": point.payload.get("note_name"),
            "heading": point.payload.get("heading"),
            "chunk_index": point.payload.get("chunk_index"),
            "text": point.payload.get("text"),
        }
        for point in response.points
    ]


def get_collection_stats() -> dict:
    """Return the configured collection name and number of indexed points."""
    info = get_qdrant_client().get_collection(COLLECTION_NAME)
    return {
        "collection": COLLECTION_NAME,
        "points_count": info.points_count or 0,
    }
