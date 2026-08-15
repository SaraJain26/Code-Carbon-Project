import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from carbon.providers import MockCarbonIntensityProvider
from api.main import app


class TestAPIEndpoints(unittest.TestCase):

    def setUp(self):
        self.patcher1 = patch("api.main.get_carbon_provider")
        self.patcher2 = patch("pipeline.pipeline.get_carbon_provider")
        self.mock_get_provider1 = self.patcher1.start()
        self.mock_get_provider2 = self.patcher2.start()
        self.mock_get_provider1.return_value = MockCarbonIntensityProvider()
        self.mock_get_provider2.return_value = MockCarbonIntensityProvider()
        self.client = TestClient(app)

    def tearDown(self):
        self.patcher1.stop()
        self.patcher2.stop()

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})

    def test_get_zones(self):
        response = self.client.get("/zones")
        self.assertEqual(response.status_code, 200)
        zones = response.json()
        self.assertIn("DK-DK1", zones)
        self.assertIn("US-NW", zones)

    def test_search_zones(self):
        response = self.client.get("/search-zones?q=Denmark")
        self.assertEqual(response.status_code, 200)
        matches = response.json()
        self.assertIn("DK-DK1", matches)

    def test_analyze_endpoint_success(self):
        code_content = (
            "def sample_function():\n"
            "    for i in range(10):\n"
            "        for j in range(10):\n"
            "            print(i, j)\n"
        )
        files = {
            "file": ("test_code.py", code_content, "text/x-python")
        }
        data = {
            "zone": "DK-DK1",
            "use_global_average": "false"
        }
        response = self.client.post("/analyze", files=files, data=data)
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["filename"], "test_code.py")
        self.assertIn("pipeline_raw", payload)
        self.assertIn("research_metrics", payload)
        self.assertIn("recommendations", payload)

        # Check that research metrics are present and correct
        metrics = payload["research_metrics"]
        self.assertIn("energy_smell_score", metrics)
        self.assertIn("carbon_impact_risk_score", metrics)
        self.assertEqual(metrics["ess_version"], "1.0.0-prototype")

        # Check recommendations are present
        recs = payload["recommendations"]["recommendations"]
        self.assertGreater(len(recs), 0)
        self.assertEqual(recs[0]["rule_id"], "EKB-COMP-001")  # Nested loops should trigger recommendation

    def test_analyze_endpoint_invalid_file(self):
        files = {
            "file": ("test_code.txt", "some text", "text/plain")
        }
        response = self.client.post("/analyze", files=files)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Only Python (.py) source files are supported", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
