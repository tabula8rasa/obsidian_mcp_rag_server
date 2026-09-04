"""Prometheus metrics exposed by the RAG API."""

from fastapi.responses import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)


SEARCH_REQUESTS = Counter(
    "rag_search_requests_total",
    "Total semantic search requests received by the RAG API.",
)
SEARCH_ERRORS = Counter(
    "rag_search_errors_total",
    "Total semantic search requests that failed.",
)
SEARCH_DURATION = Histogram(
    "rag_search_duration_seconds",
    "End-to-end RAG search duration in seconds.",
)
EMBEDDING_DURATION = Histogram(
    "rag_embedding_duration_seconds",
    "Embedding generation duration in seconds.",
    labelnames=("operation",),
)
QDRANT_SEARCH_DURATION = Histogram(
    "rag_qdrant_search_duration_seconds",
    "Time spent executing vector searches in Qdrant.",
)
SYNC_TOTAL = Counter(
    "rag_sync_total",
    "Total Vault synchronization operations.",
    labelnames=("operation",),
)
SYNC_ERRORS = Counter(
    "rag_sync_errors_total",
    "Total Vault synchronization operations that failed.",
    labelnames=("operation",),
)
SYNC_DURATION = Histogram(
    "rag_sync_duration_seconds",
    "Vault synchronization duration in seconds.",
    labelnames=("operation",),
)
INDEXED_CHUNKS = Counter(
    "rag_indexed_chunks_total",
    "Total chunks successfully processed by sync and reindex operations.",
)
LAST_SUCCESSFUL_SYNC_TIMESTAMP = Gauge(
    "rag_last_successful_sync_timestamp_seconds",
    "Unix timestamp of the last successful sync or reindex operation.",
)
IN_SYNC = Gauge(
    "rag_in_sync",
    "Whether the current Git HEAD matches the last indexed commit.",
)
QDRANT_POINTS = Gauge(
    "rag_qdrant_points",
    "Current number of points in the configured Qdrant collection.",
)


def render_metrics() -> Response:
    """Return the current registry in Prometheus exposition format."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


def update_index_gauges(points_count: int, in_sync: bool) -> None:
    """Update cached index gauges after an operational state read."""
    QDRANT_POINTS.set(points_count)
    IN_SYNC.set(1 if in_sync else 0)
