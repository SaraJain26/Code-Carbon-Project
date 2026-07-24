"""
Complexity scoring logic.

This module computes:

1. Structural Complexity Index (SCI)
2. Carbon Impact Risk Score (CIRS)
3. Risk classification
4. Sustainability recommendation
"""

from __future__ import annotations

from .models import (
    ComplexityScore,
    NormalizedComplexityMetrics,
    RiskLevel,
)

# ---------------------------------------------------------------------
# Structural Complexity Index (SCI) weights
# ---------------------------------------------------------------------

SCI_CC_WEIGHT = 0.50
SCI_ND_WEIGHT = 0.30
SCI_FD_WEIGHT = 0.20

# ---------------------------------------------------------------------
# Final Carbon Impact Risk Score (CIRS) weights
# ---------------------------------------------------------------------

SCI_WEIGHT = 0.55
ENERGY_SMELL_WEIGHT = 0.45

# ---------------------------------------------------------------------
# Risk thresholds
# ---------------------------------------------------------------------

VERY_LOW_MAX = 0.20
LOW_MAX = 0.40
MODERATE_MAX = 0.60
HIGH_MAX = 0.80


class ComplexityScorer:
    """
    Computes the final sustainability-oriented complexity score.

    The scoring process consists of two stages.

    Stage 1:
        Structural Complexity Index (SCI)

            SCI =
                0.50 * Cyclomatic Complexity
              + 0.30 * Maximum Nesting Depth
              + 0.20 * Function Density

    Stage 2:
        Carbon Impact Risk Score (CIRS)

            CIRS =
                0.55 * SCI
              + 0.45 * Energy Smell Score
    """

    @staticmethod
    def _clamp(value: float) -> float:
        """
        Clamp a score to the interval [0.0, 1.0].
        """
        return max(0.0, min(1.0, value))

    @classmethod
    def compute_structural_complexity_index(
        cls,
        metrics: NormalizedComplexityMetrics,
    ) -> float:
        """
        Compute the Structural Complexity Index (SCI).
        """

        sci = (
            SCI_CC_WEIGHT * metrics.cyclomatic_complexity
            + SCI_ND_WEIGHT * metrics.max_nesting_depth
            + SCI_FD_WEIGHT * metrics.function_density
        )

        return cls._clamp(sci)

    @classmethod
    def compute_carbon_impact_risk_score(
        cls,
        structural_complexity_index: float,
        energy_smell_score: float,
    ) -> float:
        """
        Compute the Carbon Impact Risk Score (CIRS).
        """

        score = (
            SCI_WEIGHT * structural_complexity_index
            + ENERGY_SMELL_WEIGHT * energy_smell_score
        )

        return cls._clamp(score)

    @staticmethod
    def classify_risk(score: float) -> RiskLevel:
        """
        Convert a numerical score into a qualitative risk level.
        """

        if score <= VERY_LOW_MAX:
            return RiskLevel.VERY_LOW

        if score <= LOW_MAX:
            return RiskLevel.LOW

        if score <= MODERATE_MAX:
            return RiskLevel.MODERATE

        if score <= HIGH_MAX:
            return RiskLevel.HIGH

        return RiskLevel.VERY_HIGH

    @staticmethod
    def recommendation(risk: RiskLevel) -> str:
        """
        Generate a recommendation based on the risk level.
        """

        recommendations = {
            RiskLevel.VERY_LOW:
                "Continue current development practices.",

            RiskLevel.LOW:
                "Minor optimization opportunities detected.",

            RiskLevel.MODERATE:
                "Review complex functions and energy smells.",

            RiskLevel.HIGH:
                "Refactoring recommended to improve sustainability.",

            RiskLevel.VERY_HIGH:
                (
                    "Immediate optimization strongly recommended "
                    "before deployment."
                ),
        }

        return recommendations[risk]

    @classmethod
    def score(
        cls,
        metrics: NormalizedComplexityMetrics,
    ) -> ComplexityScore:
        """
        Compute the complete complexity assessment.
        """

        sci = cls.compute_structural_complexity_index(metrics)

        cirs = cls.compute_carbon_impact_risk_score(
            sci,
            metrics.energy_smell_score,
        )

        risk = cls.classify_risk(cirs)

        recommendation = cls.recommendation(risk)

        return ComplexityScore(
            structural_complexity_index=sci,
            carbon_impact_risk_score=cirs,
            risk_level=risk,
            recommendation=recommendation,
            metrics=metrics,
        )