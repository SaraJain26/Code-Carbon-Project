from detector.context import DetectionContext
from detector.interfaces import RuleEvaluator
from detector.models import Candidate


class DefaultRuleEvaluator(RuleEvaluator):
    """
    Evaluates extracted candidates against the Energy Knowledge Base.

    Supports both:
    - Legacy generic candidate IDs (LOOP, FUNCTION, NETWORK, ...)
    - Native EKB rule IDs (EKB-COMP-001, EKB-NET-001, ...)
    """

    RULE_MAPPING = {
        "LOOP": "EKB-COMP-001",
        "FUNCTION": "EKB-COMP-002",
        "FILE": "EKB-IO-001",
        "NETWORK": "EKB-NET-001",
        "ASYNC": "EKB-ASYNC-001",
    }

    def evaluate(
        self,
        candidates: list[Candidate],
        context: DetectionContext,
    ) -> list[Candidate]:

        evaluated: list[Candidate] = []

        for candidate in candidates:

            # Candidate already contains a valid EKB rule ID.
            if context.rule_repository.get(candidate.rule_id) is not None:
                evaluated.append(candidate)
                continue

            # Legacy generic IDs.
            rule_id = self.RULE_MAPPING.get(candidate.rule_id)

            if rule_id is None:
                continue

            if context.rule_repository.get(rule_id) is None:
                continue

            evaluated.append(
                Candidate.create(
                    rule_id=rule_id,
                    confidence=candidate.confidence,
                    message=candidate.message,
                    evidence=candidate.evidence,
                    metadata=candidate.metadata,
                )
            )

        return evaluated