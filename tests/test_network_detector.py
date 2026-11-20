import unittest
from types import SimpleNamespace
from pathlib import Path

from analysis import StaticAnalysisEngine

from detector import (
    DetectionContext,
    DetectorConfiguration,
)

from detector.rules import NetworkCallDetector

from knowledge import RuleLoader, RuleRepository


FIXTURES = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "benchmarks"
)


class NetworkDetectorTest(unittest.TestCase):

    def test_flask_test_client_shaped_call_is_marked_uncertain(self):
        operation = SimpleNamespace(operation="client.get", line_number=5, caller="test_route")
        result = SimpleNamespace(
            network_operations=[operation],
            module=SimpleNamespace(source_file=Path("tests/test_routes.py")),
        )
        context = DetectionContext(
            analysis_result=result,
            rule_repository=RuleRepository(RuleLoader().load_default_rules()),
            configuration=DetectorConfiguration(),
        )

        finding = NetworkCallDetector().detect(context)[0]

        self.assertEqual(finding.confidence.value, 0.50)
        self.assertIn("may be a false positive", finding.message)

    def test_network_detection(self):

        result = StaticAnalysisEngine().analyze_file(
            FIXTURES / "async_network.py"
        )

        detector = NetworkCallDetector()

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
            "EKB-NET-001",
        )


if __name__ == "__main__":
    unittest.main()
