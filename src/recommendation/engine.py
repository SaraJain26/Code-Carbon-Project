"""
Recommendation Engine core coordinator.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING

from .models import Recommendation, RecommendationReport
from .knowledge import RULE_BEST_PRACTICES
from .prioritizer import RecommendationPrioritizer

if TYPE_CHECKING:
    from detector.models import EnergySmellReport
    from complexity.models import ComplexityScore
    from energy.models import EnergyResult
    from carbon.models import CarbonResult


class RecommendationEngine:
    """
    Consumes analysis results and generates prioritized sustainability recommendations.
    """

    def __init__(self) -> None:
        self._prioritizer = RecommendationPrioritizer()

    def generate(
        self,
        smell_report: EnergySmellReport,
        complexity: ComplexityScore,
        energy_result: EnergyResult | None = None,
        carbon_result: CarbonResult | None = None,
    ) -> RecommendationReport:
        """
        Generate a prioritized list of recommendations for the analyzed file.
        """
        # Group findings by rule ID
        findings_by_rule = defaultdict(list)
        for finding in smell_report.findings:
            findings_by_rule[finding.rule_id].append(finding)

        recommendations: list[Recommendation] = []

        for rule_id, rule_findings in findings_by_rule.items():
            # Get best practices from static mapping
            practice = RULE_BEST_PRACTICES.get(rule_id)
            if not practice:
                # If a custom rule is added, fallback to EKB rule fields
                ref_finding = rule_findings[0]
                practice = {
                    "title": ref_finding.message,
                    "explanation": ref_finding.explanation,
                    "optimization_recommendation": ref_finding.recommendation,
                    "expected_benefit": "Reduces execution energy and overhead.",
                    "code_example": None,
                    "references": [],
                }

            priority_score = self._prioritizer.compute_rule_priority(
                findings=rule_findings,
                complexity=complexity,
                energy_result=energy_result,
                carbon_result=carbon_result,
            )

            # Extract basic rule details from findings
            ref_finding = rule_findings[0]
            rec = Recommendation.create(
                rule_id=rule_id,
                title=practice["title"],
                description=ref_finding.message,
                severity=ref_finding.severity.value,
                confidence=ref_finding.confidence.value,
                category=ref_finding.category.value,
                explanation=practice["explanation"],
                optimization_recommendation=practice["optimization_recommendation"],
                expected_benefit=practice["expected_benefit"],
                code_example=practice["code_example"],
                references=practice["references"],
                priority_score=priority_score,
                findings=rule_findings,
            )
            recommendations.append(rec)

        # Sort by priority score descending
        recommendations.sort(key=lambda r: r.priority_score, reverse=True)

        # Generate developer-friendly summary
        if not recommendations:
            summary = "No energy smells detected. Your codebase adheres to sustainability best practices."
        else:
            top_rec = recommendations[0]
            summary = (
                f"Detected {len(recommendations)} areas for energy optimization. "
                f"The highest priority recommendation is '{top_rec.title}' "
                f"(Priority: {top_rec.priority_score:.6f}) targeting the '{top_rec.category}' category."
            )

        return RecommendationReport(
            recommendations=recommendations,
            summary=summary,
            generated_at=datetime.now(),
        )
