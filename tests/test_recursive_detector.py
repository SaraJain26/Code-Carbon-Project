import unittest
from pathlib import Path

from analysis import StaticAnalysisEngine

from detector import (
    DetectionContext,
    DetectorConfiguration,
)

from detector.rules import RecursiveComputationDetector

from knowledge import RuleLoader, RuleRepository


FIXTURES = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "benchmarks"
)


class RecursiveDetectorTest(unittest.TestCase):

    def test_recursive_detection(self):

        result = StaticAnalysisEngine().analyze_file(
            FIXTURES / "recursive_algorithms.py"
        )

        detector = RecursiveComputationDetector()

        context = DetectionContext(
            analysis_result=result,
            rule_repository=RuleRepository(
                RuleLoader().load_default_rules()
            ),
            configuration=DetectorConfiguration(),
        )

        findings = detector.detect(context)

        self.assertGreater(len(findings), 0)

        self.assertEqual(
            findings[0].rule_id,
            "EKB-COMP-002",
        )


if __name__ == "__main__":
    unittest.main()