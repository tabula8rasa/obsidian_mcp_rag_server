"""Non-MCP HTTP routes exposed by the server."""

from .health import register_health_route
from .metrics import register_metrics_route

__all__ = ["register_health_route", "register_metrics_route"]
