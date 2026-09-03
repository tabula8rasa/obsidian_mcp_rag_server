"""Environment-backed settings for the MCP server process."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime configuration required to construct and run the server."""

    rag_api_url: str
    rag_api_timeout_seconds: float = 30.0
    server_name: str = "Obsidian Vault Search"
    host: str = "0.0.0.0"
    port: int = 8000
    transport: str = "streamable-http"
    mcp_path: str = "/mcp"

    @classmethod
    def from_environment(cls) -> "Settings":
        """Load the settings that are configurable through the environment."""
        return cls(
            rag_api_url=os.getenv(
                "RAG_API_URL",
                "http://rag-api:8000",
            ).rstrip("/"),
        )
