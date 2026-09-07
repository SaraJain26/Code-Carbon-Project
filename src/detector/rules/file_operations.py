from detector.context import DetectionContext
from detector.models import (
    Candidate,
    CandidateEvidence,
    EvidenceKind,
)

from knowledge import RuleConfidence


class FileOperationDetector:

    RULE_ID = "EKB-IO-001"

    def detect(
        self,
        context: DetectionContext,
    ) -> list[Candidate]:

        result = context.analysis_result

        candidates: list[Candidate] = []

        for operation in result.file_operations:
            is_inside_loop = any(
                loop.line_number <= operation.line_number <= loop.end_line
                for loop in result.loops
            )

            # EKB-IO-001 targets repeated file handle initialization / open calls inside loops
            op_name = getattr(operation, "operation", str(operation))
            if not (op_name == "open" or op_name.endswith(".open") or "open" in op_name or "read_text" in op_name or "write_text" in op_name):
                continue

            conf_val = 0.90 if is_inside_loop else 0.15
            msg = "Repeated file I/O operation inside loop." if is_inside_loop else "File I/O operation detected."

            candidates.append(
                Candidate.create(
                    rule_id=self.RULE_ID,
                    confidence=RuleConfidence(conf_val),
                    message=msg,
                    evidence=[
                        CandidateEvidence(
                            kind=EvidenceKind.FILE_OPERATION,
                            source_file=result.module.source_file,
                            line_number=operation.line_number,
                        )
                    ],
                )
            )

        return candidates