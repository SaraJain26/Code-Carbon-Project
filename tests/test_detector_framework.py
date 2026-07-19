import unittest
from pathlib import Path

from detector import (
    Candidate,
    CandidateEvidence,
    DetectionContext,
    DetectorConfiguration,
    EnergyFinding,
    EnergySmellDetector,
    EvidenceKind,
)

from detector.interfaces import (
    CandidateExtractor,
    ConfidenceScorer,
    FindingGenerator,
    RuleEvaluator,
)

from knowledge import (
    EnergyRule,
    RuleCategory,
    RuleConfidence,
    RuleRepository,
    RuleSeverity,
    RuleVersion,
)


class DummyExtractor(CandidateExtractor):

    def extract(self, context):

        return [
            Candidate.create(
                rule_id="RULE-001",
                evidence=[
                    CandidateEvidence(
                        kind=EvidenceKind.LOOP,
                        source_file=Path("example.py"),
                        line_number=10,
                    )
                ],
                confidence=RuleConfidence(0.8),
                message="Dummy candidate",
            )
        ]


class DummyEvaluator(RuleEvaluator):

    def evaluate(self, candidates, context):

        return candidates


class DummyConfidenceScorer(ConfidenceScorer):

    def score(self, candidates, context):

        return candidates


class DummyGenerator(FindingGenerator):

    def generate(self, candidates, context):

        candidate = candidates[0]

        return [
            EnergyFinding.create(
                rule_id=candidate.rule_id,
                severity=RuleSeverity.MEDIUM,
                confidence=candidate.confidence,
                source_file=Path("example.py"),
                line_number=10,
                end_line=12,
                message="Dummy finding",
                explanation="Framework test",
                evidence=candidate.evidence,
                recommendation="None",
                category=RuleCategory.COMPUTATION,
            )
        ]


class DetectorFrameworkTest(unittest.TestCase):

    def setUp(self):

        rule = EnergyRule(
            id="RULE-001",
            name="Dummy Rule",
            description="Dummy",
            category=RuleCategory.COMPUTATION,
            severity=RuleSeverity.MEDIUM,
            confidence=RuleConfidence(0.8),
            rationale="Test",
            detection="Test",
            recommendation="Test",
            references=[],
            version=RuleVersion.parse("1.0"),
        )

        repository = RuleRepository([rule])

        self.context = DetectionContext(
            analysis_result=None,
            rule_repository=repository,
            configuration=DetectorConfiguration(),
        )

    def test_detector_pipeline(self):

        detector = EnergySmellDetector(
            extractor=DummyExtractor(),
            evaluator=DummyEvaluator(),
            scorer=DummyConfidenceScorer(),
            generator=DummyGenerator(),
        )

        report = detector.detect(self.context)

        self.assertEqual(len(report.findings), 1)

        self.assertEqual(
            report.summary.total_findings,
            1,
        )

        self.assertEqual(
            report.findings[0].rule_id,
            "RULE-001",
        )

    def test_report_statistics(self):

        detector = EnergySmellDetector(
            extractor=DummyExtractor(),
            evaluator=DummyEvaluator(),
            scorer=DummyConfidenceScorer(),
            generator=DummyGenerator(),
        )

        report = detector.detect(self.context)

        self.assertAlmostEqual(
            report.summary.average_confidence,
            0.8,
        )

        self.assertEqual(
            report.summary.total_findings,
            1,
        )


if __name__ == "__main__":
    unittest.main()