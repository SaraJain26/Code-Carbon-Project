from detector.context import DetectionContext
from detector.models import (
    Candidate,
    CandidateEvidence,
    EvidenceKind,
)
from knowledge import RuleConfidence


class AsyncOperationDetector:
    """
    Detects blocking synchronous operations (e.g. time.sleep, synchronous file/network I/O)
    inside async function workflows (EKB-ASYNC-001).
    """

    RULE_ID = "EKB-ASYNC-001"

    def detect(
        self,
        context: DetectionContext,
    ) -> list[Candidate]:
        result = context.analysis_result
        candidates: list[Candidate] = []

        for operation in result.async_operations:
            if not operation.operation.startswith("blocking:"):
                continue

            op_label = operation.operation.replace("blocking:", "")
            candidates.append(
                Candidate.create(
                    rule_id=self.RULE_ID,
                    confidence=RuleConfidence(0.85),
                    message=f"Blocking synchronous operation ('{op_label}') detected inside async function workflow.",
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