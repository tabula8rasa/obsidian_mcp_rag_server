from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .embeddings import get_embedding_model, get_vector_size
from .git_sync import (
    get_current_head,
    get_last_indexed_commit,
    reindex_vault,
    sync_vault,
)
from .settings import COLLECTION_NAME, MODEL_NAME, VAULT_PATH
from .vector_store import (
    collection_stats,
    get_client,
    initialize_collection,
    search,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_embedding_model()
    vector_size = get_vector_size()
    initialize_collection(vector_size)
    yield


app = FastAPI(
    title="Obsidian RAG API",
    version="0.3.0",
    lifespan=lifespan,
)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


@app.get("/health")
def health() -> dict:
    try:
        vault = Path(VAULT_PATH)
        if not vault.is_dir():
            raise RuntimeError(f"Vault path is not a directory: {vault}")
        get_client().get_collection(COLLECTION_NAME)
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


@app.get("/stats")
def stats() -> dict:
    try:
        result = collection_stats()
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


@app.post("/sync")
def sync() -> dict:
    try:
        return sync_vault()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@app.post("/reindex")
@app.post("/index-vault", include_in_schema=False)
def reindex() -> dict:
    try:
        return reindex_vault()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@app.post("/search")
def semantic_search(request: SearchRequest) -> dict:
    try:
        results = search(
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
