"""
Data models for the Hardware Profiling module.

These models represent:
1. Raw hardware information collected from the host system.
2. Normalized hardware metrics.
3. Final hardware scoring outputs used by later modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class HardwareProfile:
    """
    Raw hardware profile collected from the host machine.
    """

    cpu_model: str
    cpu_vendor: str

    physical_cores: int
    logical_threads: int

    cpu_frequency_ghz: float
    ram_gb: float

    operating_system: str
    architecture: str

    gpu_present: bool
    gpu_model: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NormalizedHardwareProfile:
    """
    Normalized hardware metrics.

    Every score is normalized into the range [0, 1].
    """

    core_score: float
    frequency_score: float
    ram_score: float
    gpu_score: float

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class HardwareScore:
    """
    Final hardware scoring output.

    hardware_performance_index (HPI)
        Represents normalized execution capability.

    reference_compute_power_w (RCP)
        Represents the reference compute power (Watts)
        derived from the detected processor family.
    """

    hardware_performance_index: float
    reference_compute_power_w: float

    metadata: dict[str, Any] = field(default_factory=dict)