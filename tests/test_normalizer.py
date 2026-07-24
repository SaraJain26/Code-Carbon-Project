import unittest

from complexity.models import ComplexityMetrics
from complexity.normalizer import ComplexityNormalizer


class ComplexityNormalizerTest(unittest.TestCase):

    def setUp(self):
        self.normalizer = ComplexityNormalizer()

    def test_normalization(self):

        metrics = ComplexityMetrics(
            cyclomatic_complexity=25,
            max_nesting_depth=5,
            function_count=20,
            class_count=4,
            loop_count=10,
            lines_of_code=500,
            function_density=0.10,
            energy_smell_score=5,
        )

        normalized = self.normalizer.normalize(metrics)

        self.assertAlmostEqual(
            normalized.cyclomatic_complexity,
            0.5,
        )

        self.assertAlmostEqual(
            normalized.max_nesting_depth,
            0.5,
        )

        self.assertAlmostEqual(
            normalized.function_density,
            0.5,
        )

        self.assertAlmostEqual(
            normalized.energy_smell_score,
            0.5,
        )

    def test_values_are_clamped(self):

        metrics = ComplexityMetrics(
            cyclomatic_complexity=500,
            max_nesting_depth=100,
            function_count=0,
            class_count=0,
            loop_count=0,
            lines_of_code=0,
            function_density=5.0,
            energy_smell_score=100,
        )

        normalized = self.normalizer.normalize(metrics)

        self.assertEqual(
            normalized.cyclomatic_complexity,
            1.0,
        )

        self.assertEqual(
            normalized.max_nesting_depth,
            1.0,
        )

        self.assertEqual(
            normalized.function_density,
            1.0,
        )

        self.assertEqual(
            normalized.energy_smell_score,
            1.0,
        )


if __name__ == "__main__":
    unittest.main()