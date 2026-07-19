import unittest
from pathlib import Path

from analysis import StaticAnalysisEngine

from detector import (
    DetectionContext,
    DetectorConfiguration,
    EnergySmellDetector,
)

from detector.extractors.default import DefaultCandidateExtractor
from detector.evaluators.default import DefaultRuleEvaluator
from detector.scorers import DefaultConfidenceScorer
from detector.generators.default import DefaultFindingGenerator

from knowledge import RuleLoader, RuleRepository


FIXTURES = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "benchmarks"
)


class DetectorEngineIntegrationTest(unittest.TestCase):

    def test_engine_runs_registered_detectors(self):

        result = StaticAnalysisEngine().analyze_file(
            FIXTURES / "async_network.py"
        )

        repository = RuleRepository(
            RuleLoader().load_default_rules()
        )

        context = DetectionContext(
            analysis_result=result,
            rule_repository=repository,
            configuration=DetectorConfiguration(),
        )

        detector = EnergySmellDetector(
            extractor=DefaultCandidateExtractor(),
            evaluator=DefaultRuleEvaluator(),
            scorer=DefaultConfidenceScorer(),
            generator=DefaultFindingGenerator(),
        )

        report = detector.detect(context)

        self.assertGreater(len(report.findings), 0)

        ids = {finding.rule_id for finding in report.findings}

        self.assertIn("EKB-NET-001", ids)
        self.assertIn("EKB-ASYNC-001", ids)


if __name__ == "__main__":
    unittest.main()