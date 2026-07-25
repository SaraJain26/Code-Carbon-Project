import unittest

from complexity.models import (
    ComplexityScore,
    NormalizedComplexityMetrics,
    RiskLevel,
)
from hardware_profile.models import HardwareScore

from energy.runtime import RuntimeEstimator


class RuntimeEstimatorTest(unittest.TestCase):

    def setUp(self):
        self.estimator = RuntimeEstimator()

    def test_runtime(self):

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

        runtime = self.estimator.estimate(
            complexity,
            hardware,
        )

        self.assertAlmostEqual(
            runtime.runtime,
            2.0,
        )

    def test_zero_hpi_protection(self):

        complexity = ComplexityScore(
            structural_complexity_index=0.50,
            carbon_impact_risk_score=0.40,
            risk_level=RiskLevel.LOW,
            recommendation="",
            metrics=NormalizedComplexityMetrics(
                cyclomatic_complexity=0.5,
                max_nesting_depth=0.3,
                function_density=0.2,
                energy_smell_score=0.2,
            ),
        )

        hardware = HardwareScore(
            hardware_performance_index=0.0,
            reference_compute_power_w=45.0,
        )

        runtime = self.estimator.estimate(
            complexity,
            hardware,
        )

        self.assertGreater(
            runtime.runtime,
            0,
        )


if __name__ == "__main__":
    unittest.main()