import unittest

from analysis import StaticAnalysisEngine

from detector import DetectionContext, DetectorConfiguration
from detector.rules import NestedLoopDetector

from knowledge import RuleLoader, RuleRepository


FIXTURES = (
    __import__("pathlib").Path(__file__).resolve().parents[1]
    / "examples"
    / "benchmarks"
)


class NestedLoopDetectorTest(unittest.TestCase):

    def test_nested_loop_detection(self):

        result = StaticAnalysisEngine().analyze_file(
            FIXTURES / "nested_loops.py"
        )

        detector = NestedLoopDetector()

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
            "EKB-COMP-001",
        )


if __name__ == "__main__":
    unittest.main()