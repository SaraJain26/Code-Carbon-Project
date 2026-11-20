"""
Runtime estimation.

This module estimates the relative execution runtime of a program
using the Structural Complexity Index (SCI) and the Hardware
Performance Index (HPI).

Model:

    Runtime = (SCI / HPI) * (1 + BETA * LoopOps / (LoopOps + K))

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
    LOOP_OPS_BETA = 2.0
    LOOP_OPS_K = 100.0

    def estimate(
        self,
        complexity: ComplexityScore,
        hardware: HardwareScore,
        loop_ops: float = 0.0,
    ) -> RuntimeEstimate:
        """
        Estimate relative execution runtime.

        The loop operation term assumes 10 iterations per loop level. It is a
        static relative signal, not a measured runtime.

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

        base_runtime = complexity.structural_complexity_index / hpi
        nonnegative_loop_ops = max(0.0, loop_ops)
        loop_factor = 1.0 + self.LOOP_OPS_BETA * nonnegative_loop_ops / (
            nonnegative_loop_ops + self.LOOP_OPS_K
        )
        runtime = base_runtime * loop_factor

        return RuntimeEstimate(
            runtime=runtime,
            loop_factor=loop_factor,
        )
