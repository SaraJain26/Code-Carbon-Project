"""
Data models for predictive energy estimation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RuntimeEstimate:
    """
    Relative runtime estimate.

    Runtime = SCI / HPI
    """

    runtime: float


@dataclass(slots=True)
class EnergyEstimate:
    """
    Relative energy estimate.

    Energy = Runtime × Reference Compute Power
    """

    energy_joules: float


@dataclass(slots=True)
class EnergyResult:
    """
    Complete output of the Week 7 energy estimation pipeline.
    """

    runtime: RuntimeEstimate

    energy: EnergyEstimate