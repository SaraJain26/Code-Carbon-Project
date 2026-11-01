"""
Complexity scoring logic.

This module computes:

1. Structural Complexity Index (SCI)
2. Internal Heuristic Structural-Smell Risk Score
3. Risk classification (RiskLevel)
4. Sustainability recommendation

Note: The research-validated physical Carbon Impact Risk Score (CIRS_Research = Hazard * Exposure)
is computed in `sustainability.metrics.ResearchSustainabilityMetrics`.
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
# Internal Heuristic Risk Score weights (used for qualitative RiskLevel)
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
        Internal Heuristic Risk Score

            Heuristic Risk Score =
                0.55 * SCI
              + 0.45 * Normalized Energy Smell Score (ESS / 10.0)

        This heuristic score [0, 1] is mapped to qualitative RiskLevel
        and recommendations.
        (For physical research CIRS in gCO2eq/run, see sustainability.metrics).
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
    def compute_heuristic_risk_score(
        cls,
        structural_complexity_index: float,
        energy_smell_score: float,
    ) -> float:
        """
        Compute the internal heuristic structural-smell risk score (0.55 * SCI + 0.45 * ESS/10).
        This heuristic score [0, 1] is used internally to classify qualitative RiskLevel.
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

        heuristic_score = cls.compute_heuristic_risk_score(
            sci,
            metrics.energy_smell_score,
        )

        risk = cls.classify_risk(heuristic_score)

        recommendation = cls.recommendation(risk)

        return ComplexityScore(
            structural_complexity_index=sci,
            heuristic_risk_score=heuristic_score,
            risk_level=risk,
            recommendation=recommendation,
            metrics=metrics,
        )