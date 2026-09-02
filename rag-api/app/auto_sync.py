import asyncio
import logging
from collections.abc import Callable


logger = logging.getLogger(__name__)


async def run_auto_sync(
    sync_function: Callable[[], dict],
    interval_seconds: int,
) -> None:
    if interval_seconds <= 0:
        raise ValueError("Automatic sync interval must be greater than zero")

    while True:
        await asyncio.sleep(interval_seconds)
        try:
            result = await asyncio.to_thread(sync_function)
            logger.info("Automatic vault sync completed: %s", result)
        except Exception:
            logger.exception("Automatic vault sync failed")
