"""
Provider abstraction layer for regional grid carbon intensity tracking.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Any

from carbon.models import ZoneData, CarbonIntensityData
from carbon.api import ElectricityMapsClient, AuthenticationError

# Environment key constant
API_KEY_ENVIRONMENT_VARIABLE = "ELECTRICITYMAPS_API_KEY"


class CarbonIntensityProvider(ABC):
    """
    Abstract base interface for obtaining regional grid carbon intensity data.
    """

    @abstractmethod
    def get_zone(self, zone: str) -> ZoneData:
        """Retrieve metadata for a single grid zone."""
        pass

    @abstractmethod
    def get_all_zones(self) -> dict[str, ZoneData]:
        """Retrieve all supported grid zones."""
        pass

    @abstractmethod
    def get_latest(self, zone: str) -> CarbonIntensityData:
        """Retrieve the latest carbon intensity measurements for a zone."""
        pass

    @abstractmethod
    def get_forecast(self, zone: str) -> list[CarbonIntensityData]:
        """Retrieve forecasted carbon intensity values for a zone."""
        pass

    @abstractmethod
    def search_zones(self, query: str) -> dict[str, ZoneData]:
        """Search supported zones by search terms."""
        pass


class ElectricityMapsProvider(CarbonIntensityProvider):
    """
    Production carbon intensity provider powered by the live Electricity Maps API.
    """

    def __init__(self) -> None:
        # Wrap live client
        self._client = ElectricityMapsClient()

    def get_zone(self, zone: str) -> ZoneData:
        return self._client.get_zone(zone)

    def get_all_zones(self) -> dict[str, ZoneData]:
        return self._client.get_all_zones()

    def get_latest(self, zone: str) -> CarbonIntensityData:
        return self._client.get_latest(zone)

    def get_forecast(self, zone: str) -> list[CarbonIntensityData]:
        return self._client.get_forecast(zone)

    def search_zones(self, query: str) -> dict[str, ZoneData]:
        return self._client.search_zones(query)


class MockCarbonIntensityProvider(CarbonIntensityProvider):
    """
    Deterministic mock provider returning realistic regional data for offline/fallback mode.
    """

    def __init__(self) -> None:
        self._zones = {
            "DK-DK1": ZoneData(
                zone_key="DK-DK1",
                zone_name="Denmark West",
                display_name="Denmark (West)",
                country_name="Denmark",
                country_code="DK",
                parent_zone=None,
                tier="1",
                commercially_available=True
            ),
            "US-NW": ZoneData(
                zone_key="US-NW",
                zone_name="US Northwest",
                display_name="US Northwest Region",
                country_name="United States",
                country_code="US",
                parent_zone=None,
                tier="1",
                commercially_available=True
            ),
            "IN": ZoneData(
                zone_key="IN",
                zone_name="India",
                display_name="India National Grid",
                country_name="India",
                country_code="IN",
                parent_zone=None,
                tier="1",
                commercially_available=True
            ),
            "FR": ZoneData(
                zone_key="FR",
                zone_name="France",
                display_name="France Grid",
                country_name="France",
                country_code="FR",
                parent_zone=None,
                tier="1",
                commercially_available=True
            ),
            "GLOBAL": ZoneData(
                zone_key="GLOBAL",
                zone_name="Global Average",
                display_name="Global Average Fallback",
                country_name="Global",
                country_code="GL",
                parent_zone=None,
                tier="N/A",
                commercially_available=True
            )
        }
        self._intensities = {
            "FR": 50.0,
            "DK-DK1": 150.0,
            "US-NW": 300.0,
            "IN": 435.0,
            "GLOBAL": 435.0
        }

    def get_zone(self, zone: str) -> ZoneData:
        return self._zones.get(zone, self._zones["GLOBAL"])

    def get_all_zones(self) -> dict[str, ZoneData]:
        return self._zones

    def get_latest(self, zone: str) -> CarbonIntensityData:
        zone_data = self.get_zone(zone)
        intensity = self._intensities.get(zone_data.zone_key, 435.0)
        return CarbonIntensityData(
            zone=zone_data,
            carbon_intensity=intensity,
            timestamp=datetime.now(timezone.utc),
            emission_factor_type="Measured",
            is_estimated=False,
            estimation_method="Mock Provider",
            source="Mock Electricity Maps"
        )

    def get_forecast(self, zone: str) -> list[CarbonIntensityData]:
        zone_data = self.get_zone(zone)
        base_intensity = self._intensities.get(zone_data.zone_key, 435.0)
        
        # Generate 24 hours of deterministic mock forecasts
        results: list[CarbonIntensityData] = []
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        
        for hour in range(24):
            timestamp = now + timedelta(hours=hour)
            # Cycle intensity using sine wave for diurnal variation
            variation = 30.0 * (1.0 + (hour % 12 - 6) / 6.0)
            intensity = max(10.0, base_intensity + variation)
            results.append(
                CarbonIntensityData(
                    zone=zone_data,
                    carbon_intensity=intensity,
                    timestamp=timestamp,
                    emission_factor_type="Forecasted",
                    is_estimated=True,
                    estimation_method="Mock Sine Simulation",
                    source="Mock Provider"
                )
            )
        return results

    def search_zones(self, query: str) -> dict[str, ZoneData]:
        q = query.strip().lower()
        return {
            k: v for k, v in self._zones.items()
            if q in k.lower() or q in v.country_name.lower() or q in v.display_name.lower()
        }


def get_carbon_provider() -> CarbonIntensityProvider:
    """
    Factory function to retrieve the configured CarbonIntensityProvider.
    Uses ElectricityMapsProvider if API key is present, otherwise MockCarbonIntensityProvider.
    """
    api_key = os.getenv(API_KEY_ENVIRONMENT_VARIABLE)
    
    # Switch on live API key availability
    if api_key and api_key != "mock_demo_key" and api_key != "dummy_key_for_testing":
        try:
            return ElectricityMapsProvider()
        except AuthenticationError:
            # Fallback if creation fails (e.g. invalid key check on instantiation)
            pass
            
    return MockCarbonIntensityProvider()
