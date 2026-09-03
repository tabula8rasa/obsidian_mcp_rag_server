"""Non-MCP HTTP routes exposed by the server."""

from .health import register_health_route

__all__ = ["register_health_route"]
