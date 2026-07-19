from detector.context import DetectionContext
from detector.models import (
    Candidate,
    CandidateEvidence,
    EvidenceKind,
)

from knowledge import RuleConfidence


class NestedLoopDetector:
    """
    Detect nested loops with nesting depth > 1.
    """

    RULE_ID = "EKB-COMP-001"

    def detect(
        self,
        context: DetectionContext,
    ) -> list[Candidate]:

        result = context.analysis_result

        findings: list[Candidate] = []

        for loop in result.loops:

            if loop.nesting_depth <= 1:
                continue

            findings.append(
                Candidate.create(
                    rule_id=self.RULE_ID,
                    confidence=RuleConfidence(0.90),
                    message="Nested loop detected.",
                    evidence=[
                        CandidateEvidence(
                            kind=EvidenceKind.LOOP,
                            source_file=result.module.source_file,
                            line_number=loop.line_number,
                        )
                    ],
                )
            )

        return findings