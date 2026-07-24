"""
Complexity Scoring Engine.

Coordinates normalization and scoring to produce the final
ComplexityScore for a source file.
"""

from __future__ import annotations

from .models import (
    ComplexityMetrics,
    ComplexityScore,
)
from .normalizer import ComplexityNormalizer
from .scorer import ComplexityScorer


class ComplexityEngine:
    """
    High-level entry point for the complexity scoring pipeline.

    Pipeline:

        Raw Metrics
              │
              ▼
        ComplexityNormalizer
              │
              ▼
      Normalized Metrics
              │
              ▼
        ComplexityScorer
              │
              ▼
        ComplexityScore
    """

    def __init__(self) -> None:
        self._normalizer = ComplexityNormalizer()
        self._scorer = ComplexityScorer()

    def analyze(
        self,
        metrics: ComplexityMetrics,
    ) -> ComplexityScore:
        """
        Analyze raw complexity metrics and produce the final
        complexity assessment.
        """

        normalized_metrics = self._normalizer.normalize(metrics)

        return self._scorer.score(normalized_metrics)