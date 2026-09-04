"""Prometheus metrics route registration."""

from mcp.server import MCPServer
from starlette.requests import Request
from starlette.responses import Response

from ..metrics import render_metrics


async def metrics_endpoint(_: Request) -> Response:
    """Expose the MCP process metrics in Prometheus format."""
    return render_metrics()


def register_metrics_route(server: MCPServer) -> None:
    """Register the HTTP Prometheus metrics endpoint."""
    server.custom_route("/metrics", methods=["GET"])(metrics_endpoint)
