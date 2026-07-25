"""
Runtime estimation.

This module estimates the relative execution runtime of a program
using the Structural Complexity Index (SCI) and the Hardware
Performance Index (HPI).

Model:

    Runtime = SCI / HPI

The runtime is a normalized, relative quantity intended for
comparative energy estimation rather than absolute execution time.
"""

from __future__ import annotations

from complexity.models import ComplexityScore
from hardware_profile.models import HardwareScore

from .models import RuntimeEstimate


class RuntimeEstimator:
    """
    Computes the estimated runtime.
    """

    MIN_HPI = 0.01

    def estimate(
        self,
        complexity: ComplexityScore,
        hardware: HardwareScore,
    ) -> RuntimeEstimate:
        """
        Estimate relative execution runtime.

        Parameters
        ----------
        complexity
            Complexity analysis output.

        hardware
            Hardware profiling output.

        Returns
        -------
        RuntimeEstimate
        """

        hpi = max(
            hardware.hardware_performance_index,
            self.MIN_HPI,
        )

        runtime = (
            complexity.structural_complexity_index
            / hpi
        )

        return RuntimeEstimate(
            runtime=round(runtime, 4),
        )