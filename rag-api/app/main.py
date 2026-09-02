from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .settings import COLLECTION_NAME, MODEL_NAME, VAULT_PATH
from .vault_indexer import read_vault_chunks
from .vector_store import collection_stats, get_client, replace_index, search


app = FastAPI(
    title="Obsidian RAG API",
    version="0.2.0",
)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


@app.get("/health")
def health() -> dict:
    try:
        get_client().get_collections()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Qdrant unavailable: {exc}",
        ) from exc

    return {
        "status": "ok",
        "qdrant": "ok",
        "collection": COLLECTION_NAME,
        "model": MODEL_NAME,
        "vault_path": VAULT_PATH,
    }


@app.get("/stats")
def stats() -> dict:
    try:
        result = collection_stats()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Could not read Qdrant stats: {exc}",
        ) from exc

    result["vault_path"] = VAULT_PATH
    return result


@app.post("/index-vault")
def index_vault() -> dict:
    try:
        chunks = read_vault_chunks()
        indexed = replace_index(chunks)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    notes = len({chunk.source_path for chunk in chunks})

    return {
        "status": "ok",
        "notes": notes,
        "chunks": indexed,
        "collection": COLLECTION_NAME,
    }


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
