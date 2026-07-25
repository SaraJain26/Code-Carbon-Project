"""
Reference Compute Power (RCP) classification.

This module classifies processors into common processor families
(Intel U/H/HX, AMD HS/HX, Apple M-series, etc.) and assigns a
Reference Compute Power (RCP).

RCP is NOT measured runtime power.

It is a representative reference value derived from published
processor family specifications and is used only for predictive
energy estimation.
"""

from __future__ import annotations

from .constants import (
    AMD_DESKTOP_REFERENCE_POWER_W,
    AMD_HS_REFERENCE_POWER_W,
    AMD_HX_REFERENCE_POWER_W,
    AMD_H_REFERENCE_POWER_W,
    AMD_U_REFERENCE_POWER_W,
    APPLE_M_REFERENCE_POWER_W,
    INTEL_DESKTOP_REFERENCE_POWER_W,
    INTEL_HX_REFERENCE_POWER_W,
    INTEL_H_REFERENCE_POWER_W,
    INTEL_K_REFERENCE_POWER_W,
    INTEL_P_REFERENCE_POWER_W,
    INTEL_U_REFERENCE_POWER_W,
    UNKNOWN_REFERENCE_POWER_W,
)


class ReferencePowerEstimator:
    """
    Maps a detected processor family to a Reference Compute Power (RCP).
    """

    def estimate(
        self,
        cpu_vendor: str,
        cpu_model: str,
    ) -> float:

        vendor = cpu_vendor.lower().strip()
        model = cpu_model.upper().strip()

        if vendor == "intel":
            return self._intel_power(model)

        if vendor == "amd":
            return self._amd_power(model)

        if vendor == "apple":
            return APPLE_M_REFERENCE_POWER_W

        return UNKNOWN_REFERENCE_POWER_W

    @staticmethod
    def _intel_power(model: str) -> float:
        """
        Intel processor family classification.
        """

        # Xeon Workstation / Server
        if "XEON" in model:
            return INTEL_DESKTOP_REFERENCE_POWER_W

        # Intel Core Ultra
        if "CORE ULTRA" in model:
            if model.endswith("H"):
                return INTEL_H_REFERENCE_POWER_W

            if model.endswith("U"):
                return INTEL_U_REFERENCE_POWER_W

        if model.endswith("HX"):
            return INTEL_HX_REFERENCE_POWER_W

        if model.endswith("HK"):
            return INTEL_H_REFERENCE_POWER_W

        if model.endswith("H"):
            return INTEL_H_REFERENCE_POWER_W

        if model.endswith("P"):
            return INTEL_P_REFERENCE_POWER_W

        if model.endswith("U"):
            return INTEL_U_REFERENCE_POWER_W

        if model.endswith("K"):
            return INTEL_K_REFERENCE_POWER_W

        return INTEL_DESKTOP_REFERENCE_POWER_W

    @staticmethod
    def _amd_power(model: str) -> float:
        """
        AMD processor family classification.
        """

        # Ryzen AI family
        if "RYZEN AI" in model:

            if "HX" in model:
                return AMD_HX_REFERENCE_POWER_W

            return AMD_HS_REFERENCE_POWER_W

        if model.endswith("HX"):
            return AMD_HX_REFERENCE_POWER_W

        if model.endswith("HS"):
            return AMD_HS_REFERENCE_POWER_W

        if model.endswith("H"):
            return AMD_H_REFERENCE_POWER_W

        if model.endswith("U"):
            return AMD_U_REFERENCE_POWER_W

        return AMD_DESKTOP_REFERENCE_POWER_W