"""MCP tool for semantic search over the user's Obsidian Vault."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from ..clients.rag_api import RagApiClient, RagApiError


logger = logging.getLogger("obsidian_mcp.vault_search")

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


async def execute_vault_search(
    rag_api_client: RagApiClient,
    query: str,
    limit: int = 5,
) -> dict[str, Any]:
    """Validate an MCP request and delegate it to the RAG API client."""
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
        result = await rag_api_client.search_vault(normalized_query, limit)
    except RagApiError as exc:
        raise ToolError(str(exc)) from exc

    results = result.get("results")
    result_count = len(results) if isinstance(results, list) else 0
    logger.info("search_vault completed result_count=%d", result_count)
    return result


def register_vault_search_tool(
    server: MCPServer,
    rag_api_client: RagApiClient,
) -> None:
    """Register the Vault search tool on an MCP server instance."""

    @server.tool(description=SEARCH_VAULT_DESCRIPTION)
    async def search_vault(
        query: Annotated[str, Field(min_length=1)],
        limit: Annotated[int, Field(ge=1, le=20)] = 5,
    ) -> dict[str, Any]:
        """Search the Obsidian Vault through the RAG API."""
        return await execute_vault_search(rag_api_client, query, limit)
