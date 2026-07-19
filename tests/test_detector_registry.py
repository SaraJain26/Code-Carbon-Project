import unittest
from pathlib import Path

from analysis import StaticAnalysisEngine

from detector import DetectionContext, DetectorConfiguration
from detector.rules import DetectorRegistry

from knowledge import RuleLoader, RuleRepository


FIXTURES = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "benchmarks"
)


class DetectorRegistryTest(unittest.TestCase):

    def test_registry_executes_all_detectors(self):

        result = StaticAnalysisEngine().analyze_file(
            FIXTURES / "async_network.py"
        )

        context = DetectionContext(
            analysis_result=result,
            rule_repository=RuleRepository(
                RuleLoader().load_default_rules()
            ),
            configuration=DetectorConfiguration(),
        )

        registry = DetectorRegistry()

        candidates = registry.detect(context)

        self.assertGreater(len(candidates), 0)

        rule_ids = {candidate.rule_id for candidate in candidates}

        self.assertIn("EKB-NET-001", rule_ids)
        self.assertIn("EKB-ASYNC-001", rule_ids)


if __name__ == "__main__":
    unittest.main()