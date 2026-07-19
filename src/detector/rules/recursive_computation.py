from detector.context import DetectionContext
from detector.models import (
    Candidate,
    CandidateEvidence,
    EvidenceKind,
)

from knowledge import RuleConfidence


class RecursiveComputationDetector:

    RULE_ID = "EKB-COMP-002"

    def detect(
        self,
        context: DetectionContext,
    ) -> list[Candidate]:

        result = context.analysis_result

        candidates: list[Candidate] = []

        for function in result.functions:

            if not function.is_recursive:
                continue

            candidates.append(
                Candidate.create(
                    rule_id=self.RULE_ID,
                    confidence=RuleConfidence(0.95),
                    message="Recursive computation detected.",
                    evidence=[
                        CandidateEvidence(
                            kind=EvidenceKind.FUNCTION,
                            source_file=result.module.source_file,
                            line_number=function.line_number,
                        )
                    ],
                )
            )

        return candidates