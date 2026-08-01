import unittest
from datetime import datetime, timezone

from carbon.models import (
    CarbonEstimate,
    CarbonIntensityData,
    CarbonResult,
    ZoneData,
)
from energy.models import (
    EnergyEstimate,
    EnergyResult,
    RuntimeEstimate,
)


class CarbonModelsTest(unittest.TestCase):

    def test_carbon_estimate_creation(self):

        carbon = CarbonEstimate(
            carbon_grams=0.0125,
        )

        self.assertEqual(
            carbon.carbon_grams,
            0.0125,
        )

    def test_carbon_result_creation(self):

        energy = EnergyResult(
            runtime=RuntimeEstimate(
                runtime=2.0,
            ),
            energy=EnergyEstimate(
                energy_joules=90.0,
            ),
        )

        carbon = CarbonEstimate(
            carbon_grams=0.010875,
        )

        carbon_data = CarbonIntensityData(
            zone=ZoneData(
                zone_key="IN",
                zone_name="India",
                display_name="India",
                country_name="India",
                country_code="IN",
                parent_zone=None,
                tier="2",
                commercially_available=True,
            ),
            carbon_intensity=435.0,
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            emission_factor_type="Measured",
            is_estimated=False,
            estimation_method="API",
            source="Electricity Maps",
        )

        result = CarbonResult(
            energy=energy,
            carbon=carbon,
            carbon_data=carbon_data,
            fallback_used=False,
        )

        self.assertEqual(
            result.energy.energy.energy_joules,
            90.0,
        )

        self.assertEqual(
            result.carbon.carbon_grams,
            0.010875,
        )

        self.assertEqual(
            result.carbon_data.carbon_intensity,
            435.0,
        )

        self.assertEqual(
            result.carbon_data.zone.zone_key,
            "IN",
        )

        self.assertFalse(
            result.fallback_used,
        )

        self.assertEqual(
            result.carbon_data.source,
            "Electricity Maps",
        )


if __name__ == "__main__":
    unittest.main()