import unittest

from complexity.models import (
    NormalizedComplexityMetrics,
    RiskLevel,
)
from complexity.scorer import ComplexityScorer


class ComplexityScorerTest(unittest.TestCase):

    def setUp(self):

        self.metrics = NormalizedComplexityMetrics(
            cyclomatic_complexity=0.60,
            max_nesting_depth=0.50,
            function_density=0.40,
            energy_smell_score=0.80,
        )

    def test_structural_complexity_index(self):

        sci = ComplexityScorer.compute_structural_complexity_index(
            self.metrics
        )

        expected = (
            0.50 * 0.60
            + 0.30 * 0.50
            + 0.20 * 0.40
        )

        self.assertAlmostEqual(sci, expected)

    def test_carbon_impact_risk_score(self):

        sci = ComplexityScorer.compute_structural_complexity_index(
            self.metrics
        )

        cirs = ComplexityScorer.compute_carbon_impact_risk_score(
            sci,
            self.metrics.energy_smell_score,
        )

        expected = (
            0.55 * sci
            + 0.45 * 0.80
        )

        self.assertAlmostEqual(cirs, expected)

    def test_risk_classification(self):

        self.assertEqual(
            ComplexityScorer.classify_risk(0.10),
            RiskLevel.VERY_LOW,
        )

        self.assertEqual(
            ComplexityScorer.classify_risk(0.30),
            RiskLevel.LOW,
        )

        self.assertEqual(
            ComplexityScorer.classify_risk(0.50),
            RiskLevel.MODERATE,
        )

        self.assertEqual(
            ComplexityScorer.classify_risk(0.70),
            RiskLevel.HIGH,
        )

        self.assertEqual(
            ComplexityScorer.classify_risk(0.95),
            RiskLevel.VERY_HIGH,
        )

    def test_score(self):

        score = ComplexityScorer.score(self.metrics)

        self.assertIsNotNone(score)

        self.assertTrue(
            0.0 <= score.structural_complexity_index <= 1.0
        )

        self.assertTrue(
            0.0 <= score.carbon_impact_risk_score <= 1.0
        )

        self.assertIsInstance(score.risk_level, RiskLevel)

        self.assertTrue(len(score.recommendation) > 0)


if __name__ == "__main__":
    unittest.main()