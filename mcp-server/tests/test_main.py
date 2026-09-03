import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app import main


class SearchVaultTests(unittest.IsolatedAsyncioTestCase):
    async def test_forwards_search_and_returns_rag_response(self) -> None:
        rag_response = {
            "query": "containerd snapshotter",
            "count": 1,
            "results": [
                {
                    "id": "point-id",
                    "score": 0.81,
                    "source_path": "Docker/containerd.md",
                    "note_name": "containerd",
                    "heading": "Snapshotter",
                    "chunk_index": 3,
                    "text": "Snapshotter details",
                }
            ],
        }
        response = MagicMock()
        response.json.return_value = rag_response

        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client

        with patch.object(main.httpx, "AsyncClient", return_value=client_context):
            result = await main.search_vault("  containerd snapshotter  ", 3)

        client.post.assert_awaited_once_with(
            "http://rag-api:8000/search",
            json={"query": "containerd snapshotter", "limit": 3},
        )
        response.raise_for_status.assert_called_once_with()
        self.assertEqual(result, rag_response)

    async def test_rejects_whitespace_only_query(self) -> None:
        with self.assertRaisesRegex(main.ToolError, "non-empty"):
            await main.search_vault("   ")

    async def test_reports_unavailable_rag_api(self) -> None:
        request = httpx.Request("POST", "http://rag-api:8000/search")
        client = AsyncMock()
        client.post.side_effect = httpx.ConnectError(
            "connection refused",
            request=request,
        )
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client

        with patch.object(main.httpx, "AsyncClient", return_value=client_context):
            with self.assertRaisesRegex(main.ToolError, "RAG API is unavailable"):
                await main.search_vault("containerd")


if __name__ == "__main__":
    unittest.main()
