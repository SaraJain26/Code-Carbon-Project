import os
import unittest
from carbon.providers import (
    get_carbon_provider,
    MockCarbonIntensityProvider,
    ElectricityMapsProvider,
    CarbonIntensityProvider
)


class TestCarbonProviders(unittest.TestCase):

    def setUp(self):
        self.original_env = os.environ.get("ELECTRICITYMAPS_API_KEY")

    def tearDown(self):
        if self.original_env is not None:
            os.environ["ELECTRICITYMAPS_API_KEY"] = self.original_env
        elif "ELECTRICITYMAPS_API_KEY" in os.environ:
            del os.environ["ELECTRICITYMAPS_API_KEY"]

    def test_mock_provider_behavior(self):
        provider = MockCarbonIntensityProvider()
        self.assertIsInstance(provider, CarbonIntensityProvider)

        # Test get_all_zones
        zones = provider.get_all_zones()
        self.assertIn("DK-DK1", zones)
        self.assertIn("FR", zones)

        # Test get_zone fallback
        zone_data = provider.get_zone("UNKNOWN")
        self.assertEqual(zone_data.zone_key, "GLOBAL")

        # Test get_latest intensity
        latest_dk = provider.get_latest("DK-DK1")
        self.assertEqual(latest_dk.carbon_intensity, 150.0)
        self.assertEqual(latest_dk.zone.zone_key, "DK-DK1")

        latest_fr = provider.get_latest("FR")
        self.assertEqual(latest_fr.carbon_intensity, 50.0)

        # Test get_forecast size
        forecast = provider.get_forecast("DK-DK1")
        self.assertEqual(len(forecast), 24)
        self.assertEqual(forecast[0].zone.zone_key, "DK-DK1")

        # Test search_zones
        matches = provider.search_zones("Denmark")
        self.assertIn("DK-DK1", matches)

    def test_factory_returns_mock_when_key_is_missing(self):
        if "ELECTRICITYMAPS_API_KEY" in os.environ:
            del os.environ["ELECTRICITYMAPS_API_KEY"]
            
        provider = get_carbon_provider()
        self.assertIsInstance(provider, MockCarbonIntensityProvider)

    def test_factory_returns_mock_when_key_is_demo_or_dummy(self):
        os.environ["ELECTRICITYMAPS_API_KEY"] = "mock_demo_key"
        provider = get_carbon_provider()
        self.assertIsInstance(provider, MockCarbonIntensityProvider)

        os.environ["ELECTRICITYMAPS_API_KEY"] = "dummy_key_for_testing"
        provider2 = get_carbon_provider()
        self.assertIsInstance(provider2, MockCarbonIntensityProvider)


if __name__ == "__main__":
    unittest.main()
