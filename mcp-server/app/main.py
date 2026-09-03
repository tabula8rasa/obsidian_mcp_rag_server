from __future__ import annotations

import logging
import os
from typing import Annotated, Any

import httpx
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse


RAG_API_URL = os.getenv("RAG_API_URL", "http://rag-api:8000").rstrip("/")
RAG_API_TIMEOUT_SECONDS = 30.0

SEARCH_VAULT_DESCRIPTION = """Search the user's personal Obsidian knowledge base semantically.

Use this tool when a request may depend on information, explanations,
decisions, project history, study notes, technical notes, or other knowledge
previously stored in the user's Obsidian Vault.

This tool is especially appropriate when the user refers to:
- their notes;
- something previously studied;
- something discussed or written before;
- previous project decisions;
- personal accumulated technical knowledge;
- "что у меня было про...";
- "как мы раньше разбирали...";
- "что я писал про...";
- "найди в моих заметках...";
- "напомни, как я понимал...".

Do not use this tool for ordinary general-knowledge questions that clearly do
not depend on the user's personal knowledge base.

The tool returns semantically relevant fragments from Obsidian notes along
with source paths, headings, chunk indexes, and similarity scores."""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("obsidian_mcp")

mcp = MCPServer("Obsidian Vault Search")


@mcp.tool(description=SEARCH_VAULT_DESCRIPTION)
async def search_vault(
    query: Annotated[str, Field(min_length=1)],
    limit: Annotated[int, Field(ge=1, le=20)] = 5,
) -> dict[str, Any]:
    """Search the Obsidian Vault through the existing RAG API."""
    normalized_query = query.strip()
    if not normalized_query:
        raise ToolError("query must be a non-empty string")
    if not 1 <= limit <= 20:
        raise ToolError("limit must be between 1 and 20")

    logger.info(
        "search_vault called query_length=%d limit=%d",
        len(normalized_query),
        limit,
    )

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(RAG_API_TIMEOUT_SECONDS)
        ) as client:
            response = await client.post(
                f"{RAG_API_URL}/search",
                json={"query": normalized_query, "limit": limit},
            )
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise ToolError(
            "Obsidian RAG API is unavailable: request timed out"
        ) from exc
    except httpx.RequestError as exc:
        raise ToolError(
            f"Obsidian RAG API is unavailable: {exc}"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise ToolError(
            "Obsidian RAG API search failed with HTTP "
            f"{exc.response.status_code}"
        ) from exc

    try:
        result = response.json()
    except ValueError as exc:
        raise ToolError(
            "Obsidian RAG API returned an invalid JSON response"
        ) from exc

    if not isinstance(result, dict):
        raise ToolError("Obsidian RAG API returned an unexpected response")

    results = result.get("results")
    result_count = len(results) if isinstance(results, list) else 0
    logger.info("search_vault completed result_count=%d", result_count)
    return result


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    logger.info(
        "Starting Obsidian MCP server on 0.0.0.0:8000/mcp "
        "with RAG API %s",
        RAG_API_URL,
    )
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
        streamable_http_path="/mcp",
    )
