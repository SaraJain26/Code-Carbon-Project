import unittest
from pathlib import Path

from detector import (
    Candidate,
    CandidateEvidence,
    DefaultFindingGenerator,
    DetectionContext,
    DetectorConfiguration,
    EvidenceKind,
)

from knowledge import (
    EnergyRule,
    RuleCategory,
    RuleConfidence,
    RuleRepository,
    RuleSeverity,
    RuleVersion,
)


class DefaultFindingGeneratorTest(unittest.TestCase):

    def setUp(self):

        rule = EnergyRule(
            id="EKB-COMP-001",
            name="Nested Loop",
            description="Nested loop detected.",
            category=RuleCategory.COMPUTATION,
            severity=RuleSeverity.MEDIUM,
            confidence=RuleConfidence(0.9),
            rationale="",
            detection="",
            recommendation="Optimize the loop.",
            references=[],
            version=RuleVersion.parse("1.0"),
        )

        self.context = DetectionContext(
            analysis_result=None,
            rule_repository=RuleRepository([rule]),
            configuration=DetectorConfiguration(),
        )

    def test_generate(self):

        candidate = Candidate.create(
            rule_id="EKB-COMP-001",
            confidence=RuleConfidence(0.9),
            message="candidate",
            evidence=[
                CandidateEvidence(
                    kind=EvidenceKind.LOOP,
                    source_file=Path("sample.py"),
                    line_number=42,
                )
            ],
        )

        generator = DefaultFindingGenerator()

        findings = generator.generate(
            [candidate],
            self.context,
        )

        self.assertEqual(len(findings), 1)

        finding = findings[0]

        self.assertEqual(finding.rule_id, "EKB-COMP-001")
        self.assertEqual(finding.line_number, 42)
        self.assertEqual(finding.category, RuleCategory.COMPUTATION)
        self.assertEqual(finding.severity, RuleSeverity.MEDIUM)