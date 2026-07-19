from detector.context import DetectionContext
from detector.interfaces import ConfidenceScorer
from detector.models import Candidate
from knowledge import RuleConfidence


class DefaultConfidenceScorer(ConfidenceScorer):
    """
    Default confidence scorer.

    This scorer estimates confidence in the detector's finding.
    It does NOT estimate computational complexity.

    Confidence is adjusted only according to the amount of
    evidence supporting a detected energy smell.
    """

    MIN_CONFIDENCE = 0.50
    MAX_CONFIDENCE = 1.00
    BONUS_PER_EXTRA_EVIDENCE = 0.02
    MAX_BONUS = 0.10

    def score(
        self,
        candidates: list[Candidate],
        context: DetectionContext,
    ) -> list[Candidate]:

        scored: list[Candidate] = []

        for candidate in candidates:

            evidence_count = len(candidate.evidence)

            bonus = min(
                max(evidence_count - 1, 0)
                * self.BONUS_PER_EXTRA_EVIDENCE,
                self.MAX_BONUS,
            )

            new_confidence = max(
                self.MIN_CONFIDENCE,
                min(
                    self.MAX_CONFIDENCE,
                    candidate.confidence.value + bonus,
                ),
            )

            scored.append(
                Candidate.create(
                    rule_id=candidate.rule_id,
                    confidence=RuleConfidence(
                        value=new_confidence,
                        rationale=candidate.confidence.rationale,
                    ),
                    message=candidate.message,
                    evidence=candidate.evidence,
                    metadata=candidate.metadata,
                )
            )

        return scored