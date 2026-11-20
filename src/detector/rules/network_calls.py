from detector.context import DetectionContext
from detector.models import (
    Candidate,
    CandidateEvidence,
    EvidenceKind,
)

from knowledge import RuleConfidence


class NetworkCallDetector:

    RULE_ID = "EKB-NET-001"

    def detect(
        self,
        context: DetectionContext,
    ) -> list[Candidate]:

        result = context.analysis_result

        candidates: list[Candidate] = []

        for operation in result.network_operations:
            client_method = operation.operation.rsplit(".", 1)[-1].lower()
            possible_flask_test_client = (
                operation.operation.lower().startswith("client.")
                and client_method in {"get", "post"}
            )
            ambiguous_receiver = operation.operation.split(".", 1)[0].lower() in {"client", "session"}
            confidence = 0.50 if possible_flask_test_client or ambiguous_receiver else 0.90

            candidates.append(
                Candidate.create(
                    rule_id=self.RULE_ID,
                    confidence=RuleConfidence(confidence),
                    message=(
                        "Network operation detected; may be a false positive because client.get/post "
                        "can be a Flask test-client call."
                        if possible_flask_test_client
                        else "Network operation detected; verify the receiver type because a generic session/client method may be local application state."
                        if ambiguous_receiver
                        else "Network operation detected."
                    ),
                    evidence=[
                        CandidateEvidence(
                            kind=EvidenceKind.NETWORK_OPERATION,
                            source_file=result.module.source_file,
                            line_number=operation.line_number,
                        )
                    ],
                )
            )

        return candidates
