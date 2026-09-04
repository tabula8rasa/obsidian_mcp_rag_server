import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from prometheus_client import generate_latest

from app.api import routes
from app.main import app
from app.metrics import SEARCH_REQUESTS


class ObservabilityApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_metrics_endpoint_returns_prometheus_metrics(self) -> None:
        response = self.client.get("/metrics")

        self.assertEqual(response.status_code, 200)
        self.assertIn("rag_search_requests_total", response.text)
        self.assertIn("rag_sync_duration_seconds", response.text)

    def test_successful_search_increments_counter_without_query_label(self) -> None:
        private_query = "private-query-that-must-not-be-a-label"
        before = SEARCH_REQUESTS._value.get()

        with patch.object(routes, "search_chunks", return_value=[]):
            response = self.client.post(
                "/search",
                json={"query": private_query, "limit": 3},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SEARCH_REQUESTS._value.get(), before + 1)
        self.assertNotIn(private_query, generate_latest().decode("utf-8"))

    def test_existing_endpoints_remain_registered(self) -> None:
        registered_paths = set(app.openapi()["paths"])

        self.assertTrue(
            {"/search", "/sync", "/reindex", "/health", "/stats"}
            <= registered_paths
        )


if __name__ == "__main__":
    unittest.main()
