import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from app.auto_sync import run_auto_sync


class AutoSyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_runs_sync_after_interval(self) -> None:
        sync_function = Mock(return_value={"status": "ok"})

        with (
            patch(
                "app.auto_sync.asyncio.sleep",
                new=AsyncMock(side_effect=[None, asyncio.CancelledError]),
            ) as sleep,
            patch(
                "app.auto_sync.asyncio.to_thread",
                new=AsyncMock(return_value={"status": "ok"}),
            ) as to_thread,
        ):
            with self.assertRaises(asyncio.CancelledError):
                await run_auto_sync(sync_function, 300)

        sleep.assert_awaited()
        to_thread.assert_awaited_once_with(sync_function)

    async def test_continues_after_sync_failure(self) -> None:
        sync_function = Mock()

        with (
            patch(
                "app.auto_sync.asyncio.sleep",
                new=AsyncMock(
                    side_effect=[None, None, asyncio.CancelledError]
                ),
            ),
            patch(
                "app.auto_sync.asyncio.to_thread",
                new=AsyncMock(
                    side_effect=[RuntimeError("Qdrant unavailable"), {"status": "ok"}]
                ),
            ) as to_thread,
            patch("app.auto_sync.logger.exception") as log_exception,
        ):
            with self.assertRaises(asyncio.CancelledError):
                await run_auto_sync(sync_function, 300)

        self.assertEqual(to_thread.await_count, 2)
        log_exception.assert_called_once_with("Automatic vault sync failed")

    async def test_rejects_non_positive_interval(self) -> None:
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            await run_auto_sync(Mock(), 0)
