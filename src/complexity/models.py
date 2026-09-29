from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(Enum):
    """
    Qualitative interpretation of the Carbon Impact Risk Score.
    """

    VERY_LOW = "Very Low"
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    VERY_HIGH = "Very High"


@dataclass(frozen=True)
class ComplexityMetrics:
    """
    Raw complexity metrics collected from the static analysis engine
    before normalization.
    """

    cyclomatic_complexity: float

    max_nesting_depth: int

    function_count: int

    class_count: int

    loop_count: int

    lines_of_code: int

    function_density: float

    energy_smell_score: float

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedComplexityMetrics:
    """
    Complexity metrics after normalization.
    All values are expected to lie in the range [0.0, 1.0].
    """

    cyclomatic_complexity: float

    max_nesting_depth: float

    function_density: float

    energy_smell_score: float

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ComplexityScore:
    """
    Final output of the Complexity Scoring Engine.

    Attributes
    ----------
    structural_complexity_index
        Structural Complexity Index (SCI).

    heuristic_risk_score
        Internal heuristic structural-smell risk score (0.55 * SCI + 0.45 * ESS/10).

    risk_level
        Qualitative interpretation of the heuristic risk score.

    recommendation
        Human-readable recommendation for improving sustainability.

    metrics
        Normalized metrics used for scoring.

    metadata
        Optional implementation-specific information.
    """
    structural_complexity_index: float

    heuristic_risk_score: float

    risk_level: RiskLevel

    recommendation: str

    metrics: NormalizedComplexityMetrics

    metadata: dict[str, Any] = field(default_factory=dict)