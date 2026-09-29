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

        # Check recommendations and optimized_file_url are present
        recs = payload["recommendations"]["recommendations"]
        self.assertGreater(len(recs), 0)
        self.assertEqual(recs[0]["rule_id"], "EKB-COMP-001")  # Nested loops should trigger recommendation
        self.assertIn("optimized_file_url", payload)
        self.assertTrue(payload["optimized_file_url"].startswith("/download-optimized/"))

        # Test download endpoint with generated optimized file
        opt_url = payload["optimized_file_url"]
        download_res = self.client.get(opt_url)
        self.assertEqual(download_res.status_code, 200)
        self.assertIn("def sample_function", download_res.text)

    def test_analyze_endpoint_invalid_file(self):
        files = {
            "file": ("test_code.txt", "some text", "text/plain")
        }
        response = self.client.post("/analyze", files=files)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Only Python (.py) source files are supported", response.json()["detail"])

    def test_download_optimized_not_found(self):
        response = self.client.get("/download-optimized/non_existent_file.py")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Optimized file not found.")

    def test_analyze_project_zip(self):
        import io
        import zipfile
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("module_a.py", "def a(): return [i*2 for i in range(100)]")
            zf.writestr("module_b.py", "def b():\n  for x in range(10):\n    for y in range(10):\n      pass")

        zip_bytes = zip_buffer.getvalue()
        files = {
            "file": ("test_project.zip", zip_bytes, "application/zip")
        }
        data = {
            "zone": "DK-DK1",
            "use_global_average": "false"
        }
        response = self.client.post("/analyze-project", files=files, data=data)
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["project_name"], "test_project.zip")
        self.assertEqual(payload["total_files"], 2)
        self.assertEqual(payload["successful_files"], 2)
        self.assertEqual(payload["error_files"], 0)
        self.assertIn("avg_sci", payload)
        self.assertIn("avg_ess", payload)
        self.assertIn("avg_cirs", payload)
        self.assertIn("total_cirs", payload)
        self.assertEqual(len(payload["files"]), 2)

    def test_analyze_project_partial_failure(self):
        import io
        import zipfile
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("valid.py", "def v(): return 42")
            zf.writestr("invalid.py", "def broken_syntax(:\n  return 0")

        zip_bytes = zip_buffer.getvalue()
        files = {
            "file": ("partial_project.zip", zip_bytes, "application/zip")
        }
        response = self.client.post("/analyze-project", files=files)
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["total_files"], 2)
        self.assertEqual(payload["successful_files"], 1)
        self.assertEqual(payload["error_files"], 1)
        
        # Verify valid file succeeded and invalid file recorded error cleanly
        files_dict = {f["filename"]: f for f in payload["files"]}
        self.assertEqual(files_dict["valid.py"]["status"], "success")
        self.assertEqual(files_dict["invalid.py"]["status"], "error")
        self.assertIsNotNone(files_dict["invalid.py"]["error_message"])

    def test_forecast_endpoint_success(self):
        response = self.client.get("/forecast?zone=IN&energy_joules=268.75")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["zone"], "IN")
        self.assertIn("current_carbon_intensity", payload)
        self.assertIn("lowest_forecast_intensity", payload)
        self.assertIn("percentage_reduction", payload)
        self.assertIn("recommended_execution_time", payload)
        self.assertIn("hourly_forecasts", payload)

        forecasts = payload["hourly_forecasts"]
        self.assertGreater(len(forecasts), 0)
        
        # Verify recommended_execution_time matches the forecast entry with lowest intensity
        lowest_entry = min(forecasts, key=lambda item: item["carbon_intensity"])
        self.assertEqual(payload["lowest_forecast_intensity"], lowest_entry["carbon_intensity"])
        self.assertEqual(payload["recommended_execution_time"], lowest_entry["timestamp"])


if __name__ == "__main__":
    unittest.main()
