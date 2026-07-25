"""
Hardware metric normalization.

This module converts raw hardware measurements into normalized scores
within the range [0, 1] and computes the Hardware Performance Index (HPI).

HPI is calculated as the arithmetic mean of the normalized hardware
characteristics.
"""

from __future__ import annotations

from .constants import (
    GPU_ABSENT_SCORE,
    GPU_PRESENT_SCORE,
    MAX_CPU_CORES,
    MAX_CPU_FREQUENCY_GHZ,
    MAX_RAM_GB,
)
from .models import (
    HardwareProfile,
    HardwareScore,
    NormalizedHardwareProfile,
)


class HardwareNormalizer:
    """
    Normalizes hardware metrics and computes the Hardware Performance Index.
    """

    @staticmethod
    def _clamp(value: float) -> float:
        """
        Clamp a value into the interval [0, 1].
        """

        return max(0.0, min(value, 1.0))

    def normalize(
        self,
        profile: HardwareProfile,
    ) -> NormalizedHardwareProfile:
        """
        Normalize raw hardware metrics.
        """

        core_score = self._clamp(
            profile.physical_cores / MAX_CPU_CORES
        )

        frequency_score = self._clamp(
            profile.cpu_frequency_ghz / MAX_CPU_FREQUENCY_GHZ
        )

        ram_score = self._clamp(
            profile.ram_gb / MAX_RAM_GB
        )

        gpu_score = (
            GPU_PRESENT_SCORE
            if profile.gpu_present
            else GPU_ABSENT_SCORE
        )

        return NormalizedHardwareProfile(
            core_score=core_score,
            frequency_score=frequency_score,
            ram_score=ram_score,
            gpu_score=gpu_score,
            metadata={
                "normalization": "min-max",
                "range": "[0,1]",
            },
        )

    def compute_hardware_score(
        self,
        normalized: NormalizedHardwareProfile,
        reference_compute_power_w: float,
    ) -> HardwareScore:
        """
        Compute the Hardware Performance Index (HPI).

        HPI is the arithmetic mean of the normalized metrics.
        """

        hpi = (
            normalized.core_score
            + normalized.frequency_score
            + normalized.ram_score
            + normalized.gpu_score
        ) / 4.0

        return HardwareScore(
            hardware_performance_index=round(hpi, 4),
            reference_compute_power_w=reference_compute_power_w,
            metadata={
                "method": "arithmetic_mean",
            },
        )