import unittest
from pathlib import Path

from analysis import StaticAnalysisEngine

from detector import (
    DetectionContext,
    DetectorConfiguration,
)

from detector.rules import AsyncOperationDetector

from knowledge import RuleLoader, RuleRepository


FIXTURES = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "benchmarks"
)


class AsyncDetectorTest(unittest.TestCase):

    def test_async_detection(self):

        result = StaticAnalysisEngine().analyze_file(
            FIXTURES / "async_network.py"
        )

        detector = AsyncOperationDetector()

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
            "EKB-ASYNC-001",
        )


if __name__ == "__main__":
    unittest.main()