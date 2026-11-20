import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from carbon.providers import MockCarbonIntensityProvider
from api.main import app


class TestAPIEndpoints(unittest.TestCase):

    def setUp(self):
        self.env_patcher = patch.dict(os.environ, {"ELECTRICITYMAPS_API_KEY": ""})
        self.env_patcher.start()
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
        self.env_patcher.stop()

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
        for key in ("carbon_before", "carbon_after_now", "carbon_after_green", "window_start", "window_end",
                    "code_only_pct", "schedule_only_pct", "total_pct", "green_window_intensity"):
            self.assertIn(key, payload)
        estimate = payload["post_refactor_estimation"]
        intensity_now = payload["pipeline_raw"]["carbon_result"]["carbon_data"]["carbon_intensity"]
        expected_now = estimate["energy_after_kwh"] * intensity_now
        self.assertAlmostEqual(payload["carbon_after_now"], expected_now, places=5)
        rows = (payload["carbon_before"], payload["carbon_after_now"], payload["carbon_after_green"])
        before, after_now, after_green = rows
        self.assertEqual(payload["code_only_pct"], round((before - after_now) / before * 100, 2) if before else 0.0)
        self.assertEqual(payload["schedule_only_pct"], round((after_now - after_green) / after_now * 100, 2) if after_now else 0.0)
        self.assertEqual(payload["total_pct"], round((before - after_green) / before * 100, 2) if before else 0.0)
        self.assertIn("cirs_before", payload)
        self.assertIn("cirs_after", payload)
        self.assertEqual(payload["execution_status"], "not_executed")
        self.assertEqual(estimate["carbon_metadata"]["source_type"], "mock")
        self.assertTrue(estimate["carbon_metadata"]["is_mock"])
        raw_findings = payload["pipeline_raw"]["energy_smell_report"]["findings"]
        self.assertEqual(estimate["finding_locations_before"], len(raw_findings))
        self.assertEqual(estimate["rule_count_before"], len({finding["rule_id"] for finding in raw_findings}))

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

    def test_no_transformer_fix_keeps_modeled_before_after_equal(self):
        files = {"file": ("unchanged.py", "def value():\n    return 42\n", "text/x-python")}
        response = self.client.post("/analyze", files=files, data={"zone": "DK-DK1", "use_global_average": "false"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["auto_applied_fixes"], [])
        estimate = payload["post_refactor_estimation"]
        self.assertEqual(estimate["energy_before_joules"], estimate["energy_after_joules"])
        self.assertEqual(estimate["cirs_before"], estimate["cirs_after"])
        self.assertEqual(payload["carbon_before"], payload["carbon_after_now"])

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
        self.assertIn("total_rule_count", payload)
        self.assertIn("project_before", payload)
        self.assertIn("project_after", payload)
        self.assertIn("project_delta", payload)
        self.assertEqual(len(payload["files"]), 2)
        accepted_statuses = {"applied", "rejected_no_improvement", "rejected_regression", "not_auto_fixable"}
        for project_file in payload["files"]:
            self.assertIn("rule_count", project_file)
            if project_file["status"] == "success":
                self.assertIn(project_file["fix_status"], accepted_statuses)
                self.assertTrue(project_file["fix_reason"])
                for metric in ("energy", "cirs", "ess"):
                    self.assertIn(metric, payload["project_before"])
                    self.assertIn(metric, payload["project_after"])
                    self.assertIn(metric, payload["project_delta"])
                single = project_file["single_file_response"]
                location_count = single["pipeline_raw"]["energy_smell_report"]["summary"]["total_findings"]
                self.assertEqual(project_file["findings_count"], location_count)
                self.assertEqual(
                    project_file["findings_count"],
                    single["post_refactor_estimation"]["finding_locations_before"],
                )
        self.assertAlmostEqual(
            payload["project_before"]["energy"],
            sum(item["before_energy"] for item in payload["files"] if item["status"] == "success"),
        )
        self.assertAlmostEqual(
            payload["project_after"]["energy"],
            sum(item["after_energy"] for item in payload["files"] if item["status"] == "success"),
        )
        self.assertAlmostEqual(
            payload["project_delta"]["energy"],
            payload["project_after"]["energy"] - payload["project_before"]["energy"],
        )
        self.assertEqual(payload["carbon_source_type"], "mock")
        self.assertEqual(payload["carbon_zone"], "DK-DK1")

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
