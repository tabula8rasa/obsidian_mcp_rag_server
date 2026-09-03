import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.clients.rag_api import RagApiClient, RagApiError


class RagApiClientTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.rag_api_client = RagApiClient(
            base_url="http://rag-api:8000/",
            timeout_seconds=30.0,
        )

    async def test_forwards_search_and_returns_rag_response(self) -> None:
        rag_response = {
            "query": "containerd snapshotter",
            "count": 1,
            "results": [{"source_path": "Docker/containerd.md"}],
        }
        response = MagicMock()
        response.json.return_value = rag_response

        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client

        with patch(
            "app.clients.rag_api.httpx.AsyncClient",
            return_value=client_context,
        ):
            result = await self.rag_api_client.search_vault(
                "containerd snapshotter",
                3,
            )

        client.post.assert_awaited_once_with(
            "http://rag-api:8000/search",
            json={"query": "containerd snapshotter", "limit": 3},
        )
        response.raise_for_status.assert_called_once_with()
        self.assertEqual(result, rag_response)

    async def test_reports_unavailable_rag_api(self) -> None:
        request = httpx.Request("POST", "http://rag-api:8000/search")
        client = AsyncMock()
        client.post.side_effect = httpx.ConnectError(
            "connection refused",
            request=request,
        )
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client

        with patch(
            "app.clients.rag_api.httpx.AsyncClient",
            return_value=client_context,
        ):
            with self.assertRaisesRegex(
                RagApiError,
                "RAG API is unavailable",
            ):
                await self.rag_api_client.search_vault("containerd", 5)

    async def test_rejects_non_object_json_response(self) -> None:
        response = MagicMock()
        response.json.return_value = []

        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client

        with patch(
            "app.clients.rag_api.httpx.AsyncClient",
            return_value=client_context,
        ):
            with self.assertRaisesRegex(RagApiError, "unexpected response"):
                await self.rag_api_client.search_vault("containerd", 5)


if __name__ == "__main__":
    unittest.main()
