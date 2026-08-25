"""
Data models for the Recommendation Engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from detector.models import EnergyFinding


@dataclass(frozen=True)
class Recommendation:
    """
    A prioritized code optimization recommendation.
    """

    recommendation_id: str
    rule_id: str
    title: str
    description: str
    severity: str
    confidence: float
    category: str
    explanation: str
    optimization_recommendation: str
    expected_benefit: str
    code_example: str | None
    references: list[dict[str, Any]]
    priority_score: float
    findings: list[EnergyFinding] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        rule_id: str,
        title: str,
        description: str,
        severity: str,
        confidence: float,
        category: str,
        explanation: str,
        optimization_recommendation: str,
        expected_benefit: str,
        code_example: str | None,
        references: list[dict[str, Any]],
        priority_score: float,
        findings: list[EnergyFinding],
    ) -> Recommendation:
        """
        Create a recommendation with a generated unique ID.
        """
        return cls(
            recommendation_id=f"rec-{uuid4()}",
            rule_id=rule_id,
            title=title,
            description=description,
            severity=severity,
            confidence=confidence,
            category=category,
            explanation=explanation,
            optimization_recommendation=optimization_recommendation,
            expected_benefit=expected_benefit,
            code_example=code_example,
            references=references,
            priority_score=priority_score,
            findings=findings,
        )


@dataclass(frozen=True)
class RecommendationReport:
    """
    The collection of prioritized recommendations generated for a codebase.
    """

    recommendations: list[Recommendation]
    summary: str
    generated_at: datetime = field(default_factory=datetime.now)
