import logging
from .core.logging import configure_logging
from .core.settings import Settings
from .server import create_server


configure_logging()
logger = logging.getLogger("obsidian_mcp")
settings = Settings.from_environment()
mcp = create_server(settings)


def run() -> None:
    """Run the configured MCP server process."""
    logger.info(
        "Starting Obsidian MCP server on %s:%d%s with RAG API %s",
        settings.host,
        settings.port,
        settings.mcp_path,
        settings.rag_api_url,
    )
    mcp.run(
        transport=settings.transport,
        host=settings.host,
        port=settings.port,
        streamable_http_path=settings.mcp_path,
    )


if __name__ == "__main__":
    run()
