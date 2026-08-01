import unittest
from datetime import datetime, timezone

from carbon.api import ElectricityMapsClient
from carbon.engine import CarbonEstimationEngine
from carbon.models import CarbonIntensityData, ZoneData
from complexity.models import (
    ComplexityScore,
    NormalizedComplexityMetrics,
    RiskLevel,
)
from energy.engine import EnergyEstimationEngine
from hardware_profile.models import HardwareScore


class FakeElectricityMapsClient(ElectricityMapsClient):

    def __init__(self):
        pass

    def get_latest(self, zone: str) -> CarbonIntensityData:

        return CarbonIntensityData(
            zone=ZoneData(
                zone_key=zone,
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


class CarbonEngineTest(unittest.TestCase):

    def setUp(self):

        self.energy_engine = EnergyEstimationEngine()
        self.carbon_engine = CarbonEstimationEngine(
            FakeElectricityMapsClient(),
        )

    def test_pipeline(self):

        complexity = ComplexityScore(
            structural_complexity_index=0.80,
            carbon_impact_risk_score=0.60,
            risk_level=RiskLevel.MODERATE,
            recommendation="",
            metrics=NormalizedComplexityMetrics(
                cyclomatic_complexity=0.8,
                max_nesting_depth=0.6,
                function_density=0.4,
                energy_smell_score=0.5,
            ),
        )

        hardware = HardwareScore(
            hardware_performance_index=0.40,
            reference_compute_power_w=45.0,
        )

        energy_result = self.energy_engine.analyze(
            complexity,
            hardware,
        )

        carbon_result = self.carbon_engine.analyze(
            energy_result=energy_result,
            zone="IN",
        )

        self.assertAlmostEqual(
            carbon_result.energy.energy.energy_joules,
            90.0,
        )

        expected = (
            (90.0 / 3_600_000.0)
            * 435.0
        )

        self.assertAlmostEqual(
            carbon_result.carbon.carbon_grams,
            round(expected, 8),
        )

        self.assertEqual(
            carbon_result.carbon_data.carbon_intensity,
            435.0,
        )

        self.assertEqual(
            carbon_result.carbon_data.zone.zone_key,
            "IN",
        )

        self.assertFalse(
            carbon_result.fallback_used,
        )

        self.assertEqual(
            carbon_result.carbon_data.source,
            "Electricity Maps",
        )


if __name__ == "__main__":
    unittest.main()