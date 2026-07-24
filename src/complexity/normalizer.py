from __future__ import annotations

from complexity.models import (
    ComplexityMetrics,
    NormalizedComplexityMetrics,
)


class ComplexityNormalizer:
    """
    Normalize raw complexity metrics into the range [0.0, 1.0].
    """

    MAX_CYCLOMATIC_COMPLEXITY = 50.0
    MAX_NESTING_DEPTH = 10.0
    MAX_FUNCTION_DENSITY = 0.20
    MAX_ENERGY_SMELL_SCORE = 10.0

    @staticmethod
    def _normalize(value: float, maximum: float) -> float:
        """
        Normalize a value into the range [0, 1].
        """

        if maximum <= 0:
            raise ValueError("Normalization maximum must be positive.")

        return min(value / maximum, 1.0)

    def normalize(
        self,
        metrics: ComplexityMetrics,
    ) -> NormalizedComplexityMetrics:

        return NormalizedComplexityMetrics(
            cyclomatic_complexity=self._normalize(
                metrics.cyclomatic_complexity,
                self.MAX_CYCLOMATIC_COMPLEXITY,
            ),
            max_nesting_depth=self._normalize(
                metrics.max_nesting_depth,
                self.MAX_NESTING_DEPTH,
            ),
            function_density=self._normalize(
                metrics.function_density,
                self.MAX_FUNCTION_DENSITY,
            ),
            energy_smell_score=self._normalize(
                metrics.energy_smell_score,
                self.MAX_ENERGY_SMELL_SCORE,
            ),
            metadata=metrics.metadata.copy(),
        )