import unittest

from complexity.models import (
    ComplexityMetrics,
    ComplexityScore,
    NormalizedComplexityMetrics,
    RiskLevel,
)


class ComplexityModelsTest(unittest.TestCase):

    def test_metrics_creation(self):

        metrics = ComplexityMetrics(
            cyclomatic_complexity=12,
            max_nesting_depth=3,
            function_count=8,
            class_count=2,
            loop_count=5,
            lines_of_code=160,
            function_density=0.05,
            energy_smell_score=6,
        )

        self.assertEqual(metrics.cyclomatic_complexity, 12)
        self.assertEqual(metrics.max_nesting_depth, 3)
        self.assertEqual(metrics.function_count, 8)
        self.assertEqual(metrics.class_count, 2)
        self.assertEqual(metrics.loop_count, 5)
        self.assertEqual(metrics.lines_of_code, 160)

    def test_normalized_metrics_creation(self):

        metrics = NormalizedComplexityMetrics(
            cyclomatic_complexity=0.65,
            max_nesting_depth=0.40,
            function_density=0.55,
            energy_smell_score=0.70,
        )

        self.assertAlmostEqual(metrics.cyclomatic_complexity, 0.65)
        self.assertAlmostEqual(metrics.energy_smell_score, 0.70)

    def test_complexity_score_creation(self):

        normalized = NormalizedComplexityMetrics(
            cyclomatic_complexity=0.60,
            max_nesting_depth=0.50,
            function_density=0.45,
            energy_smell_score=0.75,
        )

        score = ComplexityScore(
            structural_complexity_index=0.54,
            carbon_impact_risk_score=0.63,
            risk_level=RiskLevel.HIGH,
            recommendation="Refactoring recommended to improve sustainability.",
            metrics=normalized,
        )

        self.assertAlmostEqual(
            score.structural_complexity_index,
            0.54,
        )

        self.assertAlmostEqual(
            score.carbon_impact_risk_score,
            0.63,
        )

        self.assertEqual(score.risk_level, RiskLevel.HIGH)

        self.assertEqual(score.metrics, normalized)


if __name__ == "__main__":
    unittest.main()