"""HTTP endpoints for health, synchronization, and semantic search."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..core.settings import COLLECTION_NAME, MODEL_NAME, VAULT_PATH
from ..infrastructure.qdrant_store import (
    get_collection_stats,
    get_qdrant_client,
    search_chunks,
)
from ..services.vault_sync import (
    get_current_head,
    get_last_indexed_commit,
    reindex_vault,
    sync_vault,
)
from .schemas import SearchRequest


router = APIRouter()


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
        result = get_collection_stats()
        current_head = get_current_head()
        last_commit = get_last_indexed_commit()
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
        return sync_vault()
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
        return reindex_vault()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.post("/search")
def search_vault(request: SearchRequest) -> dict:
    """Return the vault chunks most semantically similar to the query."""
    try:
        results = search_chunks(
            query=request.query,
            limit=request.limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    return {
        "query": request.query,
        "count": len(results),
        "results": results,
    }
