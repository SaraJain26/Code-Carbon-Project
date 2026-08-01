"""
Data models for predictive carbon estimation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from energy.models import EnergyResult


@dataclass(slots=True)
class ZoneData:
    """
    Metadata describing an Electricity Maps zone.
    """

    zone_key: str

    zone_name: str

    display_name: str

    country_name: str

    country_code: str

    parent_zone: str | None

    tier: str

    commercially_available: bool


@dataclass(slots=True)
class CarbonIntensityData:
    """
    Carbon intensity information retrieved from
    Electricity Maps.
    """

    zone: ZoneData

    carbon_intensity: float

    timestamp: datetime

    emission_factor_type: str

    is_estimated: bool

    estimation_method: str

    source: str


@dataclass(slots=True)
class CarbonEstimate:
    """
    Estimated software carbon emissions.
    """

    carbon_grams: float


@dataclass(slots=True)
class CarbonResult:
    """
    Complete carbon estimation output.
    """

    energy: EnergyResult

    carbon: CarbonEstimate

    carbon_data: CarbonIntensityData

    fallback_used: bool