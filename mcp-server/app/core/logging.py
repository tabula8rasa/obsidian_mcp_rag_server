"""Logging configuration shared by the MCP server modules."""

import logging


LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging() -> None:
    """Configure process-wide logging with the service's standard format."""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
