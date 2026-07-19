import unittest

from detector import (
    Candidate,
    CandidateEvidence,
    DefaultRuleEvaluator,
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


class DefaultRuleEvaluatorTest(unittest.TestCase):

    def setUp(self):

        rules = [
            EnergyRule(
                id="EKB-COMP-001",
                name="Loop",
                description="",
                category=RuleCategory.COMPUTATION,
                severity=RuleSeverity.MEDIUM,
                confidence=RuleConfidence(1.0),
                rationale="",
                detection="",
                recommendation="",
                references=[],
                version=RuleVersion.parse("1.0"),
            )
        ]

        self.context = DetectionContext(
            analysis_result=None,
            rule_repository=RuleRepository(rules),
            configuration=DetectorConfiguration(),
        )

    def test_rule_mapping(self):

        candidate = Candidate.create(
            rule_id="LOOP",
            confidence=RuleConfidence(1.0),
            message="loop",
            evidence=[
                CandidateEvidence(
                    kind=EvidenceKind.LOOP,
                    source_file="x.py",
                    line_number=1,
                )
            ],
        )

        evaluator = DefaultRuleEvaluator()

        result = evaluator.evaluate(
            [candidate],
            self.context,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].rule_id, "EKB-COMP-001")


if __name__ == "__main__":
    unittest.main()