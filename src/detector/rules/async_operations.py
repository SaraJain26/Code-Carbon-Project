from detector.context import DetectionContext
from detector.models import (
    Candidate,
    CandidateEvidence,
    EvidenceKind,
)

from knowledge import RuleConfidence


class AsyncOperationDetector:

    RULE_ID = "EKB-ASYNC-001"

    def detect(
        self,
        context: DetectionContext,
    ) -> list[Candidate]:

        result = context.analysis_result

        candidates: list[Candidate] = []

        for operation in result.async_operations:

            candidates.append(
                Candidate.create(
                    rule_id=self.RULE_ID,
                    confidence=RuleConfidence(0.90),
                    message="Async operation detected.",
                    evidence=[
                        CandidateEvidence(
                            kind=EvidenceKind.ASYNC_OPERATION,
                            source_file=result.module.source_file,
                            line_number=operation.line_number,
                        )
                    ],
                )
            )

        return candidates