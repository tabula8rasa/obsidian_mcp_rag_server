import unittest

from app.routes.metrics import metrics_endpoint


class MetricsRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_metrics_endpoint_returns_prometheus_metrics(self) -> None:
        response = await metrics_endpoint(None)
        body = response.body.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("mcp_tool_calls_total", body)
        self.assertIn("mcp_rag_request_duration_seconds", body)


if __name__ == "__main__":
    unittest.main()
