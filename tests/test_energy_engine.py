import unittest

from complexity.models import (
    ComplexityScore,
    NormalizedComplexityMetrics,
    RiskLevel,
)
from energy.engine import EnergyEstimationEngine
from hardware_profile.models import HardwareScore


class EnergyEngineTest(unittest.TestCase):

    def setUp(self):

        self.engine = EnergyEstimationEngine()

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

        result = self.engine.analyze(
            complexity,
            hardware,
        )

        self.assertAlmostEqual(
            result.runtime.runtime,
            2.0,
        )

        self.assertAlmostEqual(
            result.energy.energy_joules,
            90.0,
        )


if __name__ == "__main__":
    unittest.main()