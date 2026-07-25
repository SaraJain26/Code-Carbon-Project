"""
Hardware Profiling Engine.

This module orchestrates the complete hardware profiling pipeline.

Pipeline:

HardwareProfiler
        ↓
HardwareProfile
        ↓
HardwareNormalizer
        ↓
NormalizedHardwareProfile
        ↓
ReferencePowerEstimator
        ↓
HardwareScore
"""

from __future__ import annotations

from .models import (
    HardwareProfile,
    HardwareScore,
    NormalizedHardwareProfile,
)
from .normalizer import HardwareNormalizer
from .power import ReferencePowerEstimator
from .profiler import HardwareProfiler


class HardwareProfilingEngine:
    """
    Executes the complete hardware profiling workflow.
    """

    def __init__(self) -> None:
        self._profiler = HardwareProfiler()
        self._normalizer = HardwareNormalizer()
        self._power_estimator = ReferencePowerEstimator()

    def analyze(
        self,
    ) -> tuple[
        HardwareProfile,
        NormalizedHardwareProfile,
        HardwareScore,
    ]:
        """
        Execute the complete hardware profiling pipeline.

        Returns
        -------
        tuple
            (
                HardwareProfile,
                NormalizedHardwareProfile,
                HardwareScore,
            )
        """

        profile = self._profiler.profile()

        normalized = self._normalizer.normalize(profile)

        reference_power = self._power_estimator.estimate(
            profile.cpu_vendor,
            profile.cpu_model,
        )

        hardware_score = self._normalizer.compute_hardware_score(
            normalized,
            reference_power,
        )

        return (
            profile,
            normalized,
            hardware_score,
        )