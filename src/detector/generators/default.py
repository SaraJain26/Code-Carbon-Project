from detector.context import DetectionContext
from detector.interfaces import FindingGenerator
from detector.models import Candidate, EnergyFinding

from knowledge import EnergyRule


class DefaultFindingGenerator(FindingGenerator):
    """
    Converts evaluated candidates into EnergyFinding objects.
    """

    def generate(
        self,
        candidates: list[Candidate],
        context: DetectionContext,
    ) -> list[EnergyFinding]:

        findings: list[EnergyFinding] = []

        for candidate in candidates:

            rule: EnergyRule | None = context.rule_repository.get(
                candidate.rule_id
            )

            if rule is None:
                continue

            evidence = candidate.evidence[0]

            findings.append(
                EnergyFinding.create(
                    rule_id=rule.id,
                    severity=rule.severity,
                    confidence=candidate.confidence,
                    source_file=evidence.source_file,
                    line_number=evidence.line_number,
                    end_line=evidence.line_number,
                    message=rule.name,
                    explanation=rule.description,
                    evidence=candidate.evidence,
                    recommendation=rule.recommendation,
                    category=rule.category,
                )
            )

        return findings