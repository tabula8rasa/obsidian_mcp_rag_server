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

from .embeddings import embed_documents, embed_query
from .settings import COLLECTION_NAME, QDRANT_URL
from .vault_indexer import Chunk


EMBEDDING_BATCH_SIZE = 64


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)


def _create_collection(vector_size: int) -> None:
    get_client().create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE,
        ),
    )


def _ensure_source_path_index() -> None:
    client = get_client()
    info = client.get_collection(COLLECTION_NAME)
    if "source_path" in (info.payload_schema or {}):
        return

    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="source_path",
        field_schema=PayloadSchemaType.KEYWORD,
        wait=True,
    )


def initialize_collection(vector_size: int) -> None:
    client = get_client()
    if not client.collection_exists(COLLECTION_NAME):
        _create_collection(vector_size)
    _ensure_source_path_index()


def _point_id(chunk: Chunk) -> str:
    key = f"{chunk.source_path}:{chunk.chunk_index}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def index_chunks(chunks: list[Chunk]) -> int:
    client = get_client()

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


def delete_note_from_index(source_path: str) -> None:
    get_client().delete(
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


def replace_index(chunks: list[Chunk], vector_size: int) -> int:
    client = get_client()
    client.delete_collection(COLLECTION_NAME)
    _create_collection(vector_size)
    _ensure_source_path_index()
    return index_chunks(chunks)


def search(query: str, limit: int) -> list[dict]:
    query_vector = embed_query(query)
    response = get_client().query_points(
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
    info = get_client().get_collection(COLLECTION_NAME)
    return {
        "collection": COLLECTION_NAME,
        "points_count": info.points_count or 0,
    }
