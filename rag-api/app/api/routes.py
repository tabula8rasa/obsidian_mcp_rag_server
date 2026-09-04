"""HTTP endpoints for health, synchronization, metrics, and search."""

import logging
import time
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, HTTPException

from ..core.settings import COLLECTION_NAME, MODEL_NAME, VAULT_PATH
from ..infrastructure.qdrant_store import (
    get_collection_stats,
    get_qdrant_client,
    search_chunks,
)
from ..metrics import (
    INDEXED_CHUNKS,
    LAST_SUCCESSFUL_SYNC_TIMESTAMP,
    SEARCH_DURATION,
    SEARCH_ERRORS,
    SEARCH_REQUESTS,
    SYNC_DURATION,
    SYNC_ERRORS,
    SYNC_TOTAL,
    render_metrics,
    update_index_gauges,
)
from ..services.vault_sync import (
    get_current_head,
    get_last_indexed_commit,
    reindex_vault,
    sync_vault,
)
from .schemas import SearchRequest


router = APIRouter()
logger = logging.getLogger("uvicorn.error")


def _read_operational_state() -> tuple[dict, str, str | None]:
    """Read Qdrant and Git state used by status responses and gauges."""
    stats = get_collection_stats()
    current_head = get_current_head()
    last_commit = get_last_indexed_commit()
    update_index_gauges(
        points_count=stats["points_count"],
        in_sync=last_commit is not None and current_head == last_commit,
    )
    return stats, current_head, last_commit


def refresh_operational_gauges() -> None:
    """Best-effort refresh of cached gauges without affecting service health."""
    try:
        _read_operational_state()
    except Exception:
        logger.warning(
            "operational metrics refresh failed",
            exc_info=True,
        )


def _run_sync_operation(
    operation: str,
    action: Callable[[], dict],
) -> dict:
    """Run and instrument a sync or reindex operation."""
    SYNC_TOTAL.labels(operation=operation).inc()
    started_at = time.perf_counter()
    logger.info("%s started", operation)

    try:
        result = action()
    except Exception:
        SYNC_ERRORS.labels(operation=operation).inc()
        logger.exception("%s failed", operation)
        raise
    finally:
        SYNC_DURATION.labels(operation=operation).observe(
            time.perf_counter() - started_at
        )

    indexed_chunks = int(result.get("indexed_chunks", 0))
    INDEXED_CHUNKS.inc(indexed_chunks)
    LAST_SUCCESSFUL_SYNC_TIMESTAMP.set_to_current_time()
    refresh_operational_gauges()
    logger.info(
        "%s completed indexed_chunks=%d changed=%s",
        operation,
        indexed_chunks,
        result.get("changed"),
    )
    return result


@router.get("/metrics", include_in_schema=False)
def get_metrics():
    """Expose Prometheus metrics without querying operational dependencies."""
    return render_metrics()


@router.get("/health")
def get_health() -> dict:
    """Report whether the vault, Git repository, and vector store are usable."""
    try:
        vault = Path(VAULT_PATH)
        if not vault.is_dir():
            raise RuntimeError(f"Vault path is not a directory: {vault}")
        get_qdrant_client().get_collection(COLLECTION_NAME)
        get_current_head()
        last_commit = get_last_indexed_commit()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Health check failed: {exc}",
        ) from exc

    return {
        "status": "ok",
        "qdrant": "ok",
        "collection": COLLECTION_NAME,
        "vault": "ok",
        "git": "ok",
        "model": MODEL_NAME,
        "last_indexed_commit": last_commit,
    }


@router.get("/stats")
def get_stats() -> dict:
    """Return collection statistics and the current synchronization state."""
    try:
        result, current_head, last_commit = _read_operational_state()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Could not read Qdrant stats: {exc}",
        ) from exc

    result.update(
        {
            "current_git_head": current_head,
            "last_indexed_commit": last_commit,
            "in_sync": last_commit is not None and current_head == last_commit,
        }
    )
    return result


@router.post("/sync")
def sync_index() -> dict:
    """Synchronize committed vault changes with the vector index."""
    try:
        return _run_sync_operation("sync", sync_vault)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.post("/reindex")
@router.post("/index-vault", include_in_schema=False)
def reindex() -> dict:
    """Rebuild the vector index from all Markdown notes in the vault."""
    try:
        return _run_sync_operation("reindex", reindex_vault)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.post("/search")
def search_vault(request: SearchRequest) -> dict:
    """Return the vault chunks most semantically similar to the query."""
    SEARCH_REQUESTS.inc()
    started_at = time.perf_counter()
    query_length = len(request.query)
    logger.info(
        "rag search started query_length=%d limit=%d",
        query_length,
        request.limit,
    )

    try:
        results = search_chunks(
            query=request.query,
            limit=request.limit,
        )
    except Exception as exc:
        SEARCH_ERRORS.inc()
        logger.exception(
            "rag search failed query_length=%d limit=%d",
            query_length,
            request.limit,
        )
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
    finally:
        SEARCH_DURATION.observe(time.perf_counter() - started_at)

    logger.info(
        "rag search completed query_length=%d limit=%d result_count=%d",
        query_length,
        request.limit,
        len(results),
    )

    return {
        "query": request.query,
        "count": len(results),
        "results": results,
    }
