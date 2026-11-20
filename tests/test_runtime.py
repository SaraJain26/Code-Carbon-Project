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
            heuristic_risk_score=0.60,
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

    def test_zero_loop_ops_preserves_original_runtime_formula(self):
        complexity = ComplexityScore(
            structural_complexity_index=0.80,
            heuristic_risk_score=0.60,
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

        estimate = self.estimator.estimate(complexity, hardware, loop_ops=0.0)

        self.assertEqual(estimate.runtime, round(0.80 / 0.40, 4))

    def test_zero_loop_ops_factor_is_exactly_one(self):
        self.assertEqual(1.0 + RuntimeEstimator.LOOP_OPS_BETA * 0.0 / (0.0 + RuntimeEstimator.LOOP_OPS_K), 1.0)

    def test_loop_weighted_operations_increase_runtime_estimate(self):
        complexity = ComplexityScore(
            structural_complexity_index=0.80,
            heuristic_risk_score=0.60,
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

        baseline = self.estimator.estimate(complexity, hardware)
        looped = self.estimator.estimate(complexity, hardware, loop_ops=30.0)

        self.assertGreater(looped.runtime, baseline.runtime)

    def test_saturating_loop_ops_formula(self):
        complexity = ComplexityScore(
            structural_complexity_index=0.80,
            heuristic_risk_score=0.60,
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

        runtime = self.estimator.estimate(complexity, hardware, loop_ops=100.0)

        self.assertAlmostEqual(runtime.runtime, round((0.80 / 0.40) * 2.0, 4))

    def test_zero_hpi_protection(self):

        complexity = ComplexityScore(
            structural_complexity_index=0.50,
            heuristic_risk_score=0.40,
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
