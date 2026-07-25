"""
Energy estimation engine.

Coordinates the complete predictive energy estimation pipeline.

Pipeline

Complexity Score
        +
Hardware Score
        │
        ▼
Runtime Estimation
        │
        ▼
Energy Estimation
"""

from __future__ import annotations

from complexity.models import ComplexityScore
from hardware_profile.models import HardwareScore

from .estimator import EnergyEstimator
from .models import EnergyResult
from .runtime import RuntimeEstimator


class EnergyEstimationEngine:
    """
    End-to-end predictive energy estimation engine.
    """

    def __init__(self) -> None:

        self._runtime_estimator = RuntimeEstimator()
        self._energy_estimator = EnergyEstimator()

    def analyze(
        self,
        complexity: ComplexityScore,
        hardware: HardwareScore,
    ) -> EnergyResult:

        runtime = self._runtime_estimator.estimate(
            complexity,
            hardware,
        )

        energy = self._energy_estimator.estimate(
            runtime,
            hardware,
        )

        return EnergyResult(
            runtime=runtime,
            energy=energy,
        )