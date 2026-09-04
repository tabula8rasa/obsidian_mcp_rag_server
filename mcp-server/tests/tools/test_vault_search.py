import unittest
from unittest.mock import AsyncMock

from mcp.server.mcpserver.exceptions import ToolError

from app.clients.rag_api import RagApiError
from app.metrics import TOOL_CALLS, TOOL_ERRORS
from app.tools.vault_search import execute_vault_search


class VaultSearchToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_normalizes_query_and_returns_client_response(self) -> None:
        rag_response = {
            "query": "containerd snapshotter",
            "count": 0,
            "results": [],
        }
        rag_api_client = AsyncMock()
        rag_api_client.search_vault.return_value = rag_response
        calls_before = TOOL_CALLS.labels(tool="search_vault")._value.get()

        result = await execute_vault_search(
            rag_api_client,
            "  containerd snapshotter  ",
            3,
        )

        rag_api_client.search_vault.assert_awaited_once_with(
            "containerd snapshotter",
            3,
        )
        self.assertEqual(result, rag_response)
        self.assertEqual(
            TOOL_CALLS.labels(tool="search_vault")._value.get(),
            calls_before + 1,
        )

    async def test_rejects_whitespace_only_query(self) -> None:
        with self.assertRaisesRegex(ToolError, "non-empty"):
            await execute_vault_search(AsyncMock(), "   ")

    async def test_rejects_limit_outside_supported_range(self) -> None:
        with self.assertRaisesRegex(ToolError, "between 1 and 20"):
            await execute_vault_search(AsyncMock(), "containerd", 21)

    async def test_translates_rag_client_error_to_tool_error(self) -> None:
        rag_api_client = AsyncMock()
        rag_api_client.search_vault.side_effect = RagApiError(
            "Obsidian RAG API is unavailable: connection refused",
            error_type="network",
        )
        errors_before = TOOL_ERRORS.labels(
            tool="search_vault",
            type="network",
        )._value.get()

        with self.assertRaisesRegex(ToolError, "RAG API is unavailable"):
            await execute_vault_search(rag_api_client, "containerd")

        self.assertEqual(
            TOOL_ERRORS.labels(
                tool="search_vault",
                type="network",
            )._value.get(),
            errors_before + 1,
        )


if __name__ == "__main__":
    unittest.main()
