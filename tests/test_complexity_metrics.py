import unittest
from pathlib import Path

from analysis.models import (
    AnalysisResult,
    ClassInfo,
    FunctionInfo,
    LoopInfo,
    LoopType,
    ModuleInfo,
)

from complexity.metrics import ComplexityMetricsExtractor


class ComplexityMetricsExtractorTest(unittest.TestCase):

    def setUp(self):

        self.extractor = ComplexityMetricsExtractor()

    def test_extract_metrics(self):

        analysis = AnalysisResult(
            module=ModuleInfo(
                source_file=Path("example.py"),
                name="example",
                docstring=None,
                line_count=100,
            ),
            functions=[
                FunctionInfo(
                    name="a",
                    qualified_name="a",
                    line_number=1,
                    end_line=10,
                ),
                FunctionInfo(
                    name="b",
                    qualified_name="b",
                    line_number=20,
                    end_line=30,
                ),
            ],
            classes=[
                ClassInfo(
                    name="Example",
                    qualified_name="Example",
                    line_number=40,
                    end_line=60,
                )
            ],
            loops=[
                LoopInfo(
                    loop_type=LoopType.FOR,
                    line_number=5,
                    end_line=8,
                    nesting_depth=1,
                ),
                LoopInfo(
                    loop_type=LoopType.WHILE,
                    line_number=12,
                    end_line=20,
                    nesting_depth=3,
                ),
            ],
        )

        metrics = self.extractor.extract(
            analysis,
            energy_smell_score=5.0,
        )

        self.assertEqual(metrics.function_count, 2)

        self.assertEqual(metrics.class_count, 1)

        self.assertEqual(metrics.loop_count, 2)

        self.assertEqual(metrics.lines_of_code, 100)

        self.assertEqual(metrics.max_nesting_depth, 3)

        self.assertAlmostEqual(
            metrics.function_density,
            0.02,
        )

        self.assertEqual(
            metrics.energy_smell_score,
            5.0,
        )

        self.assertEqual(
            metrics.cyclomatic_complexity,
            0.0,
        )

    def test_empty_analysis(self):

        analysis = AnalysisResult(
            module=ModuleInfo(
                source_file=Path("empty.py"),
                name="empty",
                docstring=None,
                line_count=0,
            ),
        )

        metrics = self.extractor.extract(analysis)

        self.assertEqual(metrics.function_count, 0)

        self.assertEqual(metrics.class_count, 0)

        self.assertEqual(metrics.loop_count, 0)

        self.assertEqual(metrics.max_nesting_depth, 0)

        self.assertEqual(metrics.function_density, 0.0)


if __name__ == "__main__":
    unittest.main()