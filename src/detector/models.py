"""Typed models for the energy smell detection framework."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from knowledge import RuleCategory, RuleConfidence, RuleSeverity


class EvidenceKind(str, Enum):
    """Language-neutral kinds of source evidence that may support a finding."""

    LOOP = "loop"
    FUNCTION = "function"
    CALL = "call"
    FILE_OPERATION = "file_operation"
    NETWORK_OPERATION = "network_operation"
    CLASS = "class"
    ASYNC_OPERATION = "async_operation"
    EXCEPTION = "exception"
    SYMBOL = "symbol"
    CONTROL_FLOW = "control_flow"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CandidateEvidence:
    """Structural evidence collected before rule evaluation.

    Evidence is intentionally detached from Python AST node objects so detector
    findings can remain language-independent and serializable.
    """

    kind: EvidenceKind
    source_file: Path
    line_number: int | None = None
    end_line: int | None = None
    symbol_name: str | None = None
    description: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Candidate:
    """Possible rule match produced before a finding exists."""

    candidate_id: str
    rule_id: str
    evidence: list[CandidateEvidence]
    confidence: RuleConfidence
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        rule_id: str,
        evidence: list[CandidateEvidence],
        confidence: RuleConfidence,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> "Candidate":
        """Create a candidate with a generated stable-format identifier."""

        return cls(
            candidate_id=f"candidate-{uuid4()}",
            rule_id=rule_id,
            evidence=evidence,
            confidence=confidence,
            message=message,
            metadata=metadata or {},
        )


@dataclass(frozen=True)
class EnergyFinding:
    """Final detector finding linked to an EKB rule."""

    finding_id: str
    rule_id: str
    severity: RuleSeverity
    confidence: RuleConfidence
    source_file: Path
    line_number: int | None
    end_line: int | None
    message: str
    explanation: str
    evidence: list[CandidateEvidence]
    recommendation: str
    category: RuleCategory
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        rule_id: str,
        severity: RuleSeverity,
        confidence: RuleConfidence,
        source_file: Path,
        line_number: int | None,
        end_line: int | None,
        message: str,
        explanation: str,
        evidence: list[CandidateEvidence],
        recommendation: str,
        category: RuleCategory,
        metadata: dict[str, Any] | None = None,
    ) -> "EnergyFinding":
        """Create a finding with a generated stable-format identifier."""

        return cls(
            finding_id=f"finding-{uuid4()}",
            rule_id=rule_id,
            severity=severity,
            confidence=confidence,
            source_file=source_file,
            line_number=line_number,
            end_line=end_line,
            message=message,
            explanation=explanation,
            evidence=evidence,
            recommendation=recommendation,
            category=category,
            metadata=metadata or {},
        )


@dataclass(frozen=True)
class ReportStatistics:
    """Aggregate statistics for an `EnergySmellReport`."""

    total_findings: int
    findings_by_severity: dict[RuleSeverity, int]
    findings_by_category: dict[RuleCategory, int]
    average_confidence: float

    @classmethod
    def from_findings(cls, findings: list[EnergyFinding]) -> "ReportStatistics":
        """Aggregate straightforward report statistics."""

        severity_counts = Counter(finding.severity for finding in findings)
        category_counts = Counter(finding.category for finding in findings)
        average = sum(finding.confidence.value for finding in findings) / len(findings) if findings else 0.0
        return cls(
            total_findings=len(findings),
            findings_by_severity=dict(severity_counts),
            findings_by_category=dict(category_counts),
            average_confidence=average,
        )


@dataclass(frozen=True)
class EnergySmellReport:
    """Final output produced by the detector framework."""

    findings: list[EnergyFinding]
    summary: ReportStatistics
    generated_at: datetime
    detector_version: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_findings(
        cls,
        findings: list[EnergyFinding],
        detector_version: str,
        metadata: dict[str, Any] | None = None,
    ) -> "EnergySmellReport":
        """Create a report and aggregate summary statistics."""

        return cls(
            findings=findings,
            summary=ReportStatistics.from_findings(findings),
            generated_at=datetime.now(timezone.utc),
            detector_version=detector_version,
            metadata=metadata or {},
        )
