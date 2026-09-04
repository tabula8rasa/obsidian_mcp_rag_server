"""Composition of the MCP server and its dependencies."""

from mcp.server import MCPServer

from .clients.rag_api import RagApiClient
from .core.settings import Settings
from .routes.health import register_health_route
from .routes.metrics import register_metrics_route
from .tools.vault_search import register_vault_search_tool


def create_server(settings: Settings) -> MCPServer:
    """Construct a fully configured Obsidian Vault MCP server."""
    server = MCPServer(settings.server_name)
    rag_api_client = RagApiClient(
        base_url=settings.rag_api_url,
        timeout_seconds=settings.rag_api_timeout_seconds,
    )

    register_vault_search_tool(server, rag_api_client)
    register_health_route(server)
    register_metrics_route(server)
    return server
