"""Health-check route registration."""

from mcp.server import MCPServer
from starlette.requests import Request
from starlette.responses import JSONResponse


async def health_check(_: Request) -> JSONResponse:
    """Return a minimal liveness response for container health checks."""
    return JSONResponse({"status": "ok"})


def register_health_route(server: MCPServer) -> None:
    """Register the HTTP health-check endpoint on the MCP server."""
    server.custom_route("/health", methods=["GET"])(health_check)
