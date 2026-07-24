import unittest

from complexity.engine import ComplexityEngine
from complexity.models import (
    ComplexityMetrics,
    RiskLevel,
)


class ComplexityEngineTest(unittest.TestCase):

    def setUp(self):

        self.engine = ComplexityEngine()

    def test_analysis_pipeline(self):

        metrics = ComplexityMetrics(
            cyclomatic_complexity=25,
            max_nesting_depth=4,
            function_count=10,
            class_count=2,
            loop_count=7,
            lines_of_code=250,
            function_density=0.08,
            energy_smell_score=5,
        )

        result = self.engine.analyze(metrics)

        self.assertTrue(
            0.0 <= result.structural_complexity_index <= 1.0
        )

        self.assertTrue(
            0.0 <= result.carbon_impact_risk_score <= 1.0
        )

        self.assertIsInstance(result.risk_level, RiskLevel)

        self.assertTrue(len(result.recommendation) > 0)


if __name__ == "__main__":
    unittest.main()