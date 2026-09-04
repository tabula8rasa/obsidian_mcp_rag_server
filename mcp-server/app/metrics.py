"""Prometheus metrics exposed by the MCP server."""

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from starlette.responses import Response


TOOL_CALLS = Counter(
    "mcp_tool_calls_total",
    "Total MCP tool calls.",
    labelnames=("tool",),
)
TOOL_ERRORS = Counter(
    "mcp_tool_errors_total",
    "Total MCP tool call failures by bounded error type.",
    labelnames=("tool", "type"),
)
TOOL_DURATION = Histogram(
    "mcp_tool_duration_seconds",
    "End-to-end MCP tool execution duration in seconds.",
    labelnames=("tool",),
)
RAG_REQUEST_DURATION = Histogram(
    "mcp_rag_request_duration_seconds",
    "Duration of requests from MCP to the RAG API in seconds.",
)
SEARCH_RESULT_COUNT = Histogram(
    "mcp_search_result_count",
    "Number of results returned by search_vault.",
    labelnames=("tool",),
    buckets=(0, 1, 2, 3, 5, 10, 20),
)


def render_metrics() -> Response:
    """Return the current registry in Prometheus exposition format."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
