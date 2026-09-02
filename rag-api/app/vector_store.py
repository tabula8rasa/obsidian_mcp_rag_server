from __future__ import annotations

import uuid
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from .embeddings import embed_query, embed_texts
from .settings import COLLECTION_NAME, QDRANT_URL
from .vault_indexer import Chunk


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)


def _create_collection(vector_size: int) -> None:
    client = get_client()

    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE,
        ),
    )


def _point_id(chunk: Chunk) -> str:
    key = f"{chunk.source_path}:{chunk.chunk_index}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def replace_index(chunks: list[Chunk]) -> int:
    if not chunks:
        raise RuntimeError("No Markdown chunks found in the vault")

    vectors = embed_texts([chunk.text for chunk in chunks])
    _create_collection(len(vectors[0]))

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
                "modified_ns": chunk.modified_ns,
            },
        )
        for chunk, vector in zip(chunks, vectors)
    ]

    batch_size = 128
    client = get_client()

    for start in range(0, len(points), batch_size):
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points[start:start + batch_size],
            wait=True,
        )

    return len(points)


def search(query: str, limit: int) -> list[dict]:
    client = get_client()

    if not client.collection_exists(COLLECTION_NAME):
        return []

    query_vector = embed_query(query)

    response = client.query_points(
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


def collection_stats() -> dict:
    client = get_client()

    if not client.collection_exists(COLLECTION_NAME):
        return {
            "exists": False,
            "collection": COLLECTION_NAME,
            "points_count": 0,
        }

    info = client.get_collection(COLLECTION_NAME)

    return {
        "exists": True,
        "collection": COLLECTION_NAME,
        "points_count": info.points_count or 0,
    }
