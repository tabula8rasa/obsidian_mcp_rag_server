"""Asynchronous client for the Obsidian RAG API."""

from __future__ import annotations

from typing import Any

import httpx


class RagApiError(RuntimeError):
    """Raised when the RAG API cannot provide a valid search response."""


class RagApiClient:
    """Send semantic-search requests to the existing RAG API service."""

    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self._search_url = f"{base_url.rstrip('/')}/search"
        self._timeout = httpx.Timeout(timeout_seconds)

    async def search_vault(self, query: str, limit: int) -> dict[str, Any]:
        """Return the validated JSON object produced by the search endpoint."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    self._search_url,
                    json={"query": query, "limit": limit},
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise RagApiError(
                "Obsidian RAG API is unavailable: request timed out"
            ) from exc
        except httpx.RequestError as exc:
            raise RagApiError(
                f"Obsidian RAG API is unavailable: {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise RagApiError(
                "Obsidian RAG API search failed with HTTP "
                f"{exc.response.status_code}"
            ) from exc

        try:
            result = response.json()
        except ValueError as exc:
            raise RagApiError(
                "Obsidian RAG API returned an invalid JSON response"
            ) from exc

        if not isinstance(result, dict):
            raise RagApiError(
                "Obsidian RAG API returned an unexpected response"
            )

        return result
