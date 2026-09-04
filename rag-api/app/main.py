"""FastAPI application construction and startup lifecycle."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from .api.routes import refresh_operational_gauges, router
from .core.settings import VECTOR_SIZE
from .infrastructure.embedding_model import get_embedding_model
from .infrastructure.qdrant_store import ensure_collection


@asynccontextmanager
async def application_lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize shared resources before the API begins serving requests."""
    get_embedding_model()
    ensure_collection(VECTOR_SIZE)
    refresh_operational_gauges()
    yield


app = FastAPI(
    title="Obsidian RAG API",
    version="0.3.0",
    lifespan=application_lifespan,
)
app.include_router(router)
