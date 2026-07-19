import unittest
from pathlib import Path

from detector import (
    Candidate,
    CandidateEvidence,
    EvidenceKind,
)
from detector.scorers import DefaultConfidenceScorer
from knowledge import RuleConfidence


class DefaultConfidenceScorerTest(unittest.TestCase):

    def setUp(self):
        self.scorer = DefaultConfidenceScorer()

    def test_empty_candidate_list(self):
        self.assertEqual(
            self.scorer.score([], None),
            [],
        )

    def test_single_evidence_keeps_confidence(self):

        candidate = Candidate.create(
            rule_id="RULE-001",
            confidence=RuleConfidence(0.80),
            message="test",
            evidence=[
                CandidateEvidence(
                    kind=EvidenceKind.LOOP,
                    source_file=Path("example.py"),
                    line_number=10,
                )
            ],
        )

        scored = self.scorer.score([candidate], None)

        self.assertAlmostEqual(
            scored[0].confidence.value,
            0.80,
            places=2,
        )

    def test_multiple_evidence_increases_confidence(self):

        candidate = Candidate.create(
            rule_id="RULE-001",
            confidence=RuleConfidence(0.80),
            message="test",
            evidence=[
                CandidateEvidence(
                    kind=EvidenceKind.LOOP,
                    source_file=Path("example.py"),
                    line_number=10,
                ),
                CandidateEvidence(
                    kind=EvidenceKind.NETWORK_OPERATION,
                    source_file=Path("example.py"),
                    line_number=12,
                ),
                CandidateEvidence(
                    kind=EvidenceKind.FILE_OPERATION,
                    source_file=Path("example.py"),
                    line_number=18,
                ),
            ],
        )

        scored = self.scorer.score([candidate], None)

        self.assertGreater(
            scored[0].confidence.value,
            0.80,
        )

    def test_confidence_is_clamped_to_one(self):

        candidate = Candidate.create(
            rule_id="RULE-001",
            confidence=RuleConfidence(0.98),
            message="test",
            evidence=[
                CandidateEvidence(
                    kind=EvidenceKind.LOOP,
                    source_file=Path("example.py"),
                    line_number=10,
                ),
                CandidateEvidence(
                    kind=EvidenceKind.NETWORK_OPERATION,
                    source_file=Path("example.py"),
                    line_number=11,
                ),
                CandidateEvidence(
                    kind=EvidenceKind.FILE_OPERATION,
                    source_file=Path("example.py"),
                    line_number=12,
                ),
                CandidateEvidence(
                    kind=EvidenceKind.ASYNC_OPERATION,
                    source_file=Path("example.py"),
                    line_number=13,
                ),
                CandidateEvidence(
                    kind=EvidenceKind.CALL,
                    source_file=Path("example.py"),
                    line_number=14,
                ),
                CandidateEvidence(
                    kind=EvidenceKind.LOOP,
                    source_file=Path("example.py"),
                    line_number=15,
                ),
            ],
        )

        scored = self.scorer.score([candidate], None)

        self.assertEqual(
            scored[0].confidence.value,
            1.0,
        )


if __name__ == "__main__":
    unittest.main()