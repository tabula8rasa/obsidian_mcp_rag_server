"""Request schemas for the HTTP API."""

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Validated input for a semantic vault search."""

    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
