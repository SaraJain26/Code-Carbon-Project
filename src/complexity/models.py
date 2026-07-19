from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
    """

    raw_score: float

    normalized_score: float

    metrics: NormalizedComplexityMetrics

    metadata: dict[str, Any] = field(default_factory=dict)