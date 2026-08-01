"""
Electricity Maps API client.

Provides strongly typed access to:

- Latest carbon intensity
- Carbon intensity forecasts
- Zone metadata
- Supported zones
"""

from __future__ import annotations

import os

from datetime import datetime
from typing import Any
from types import TracebackType
from typing import Type

import requests
from dotenv import load_dotenv

from .config import (
    API_BASE_URL,
    API_KEY_ENVIRONMENT_VARIABLE,
    API_TIMEOUT_SECONDS,
)

from .models import (
    CarbonIntensityData,
    ZoneData,
)

load_dotenv()


class ElectricityMapsAPIError(Exception):
    """Base Electricity Maps API exception."""


class AuthenticationError(ElectricityMapsAPIError):
    """Raised when authentication fails."""


class InvalidZoneError(ElectricityMapsAPIError):
    """Raised when a Zone ID is invalid."""


class APIRequestError(ElectricityMapsAPIError):
    """Raised for unexpected API failures."""


class ElectricityMapsClient:
    """
    Client for the Electricity Maps API.
    """

    def __init__(self) -> None:

        api_key = os.getenv(
            API_KEY_ENVIRONMENT_VARIABLE,
        )

        if not api_key:

            raise AuthenticationError(
                "Electricity Maps API key was not found."
            )

        self._session = requests.Session()

        self._session.headers.update(
            {
                "auth-token": api_key,
                "Accept": "application/json",
            }
        )
        self._zones_cache: dict[str, ZoneData] | None = None

    def _request(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """
        Execute an authenticated GET request.
        """

        url = f"{API_BASE_URL}{endpoint}"

        try:

            response = self._session.get(
                url,
                params=params,
                timeout=API_TIMEOUT_SECONDS,
            )
        except requests.Timeout as exc:

            raise APIRequestError(
                "The Electricity Maps API request timed out."
            ) from exc
        
        except requests.RequestException as exc:

            raise APIRequestError(
                str(exc),
            ) from exc

        if response.status_code == 401:

            raise AuthenticationError(
                "Invalid Electricity Maps API key."
            )

        if response.status_code == 404:

            raise InvalidZoneError(
                "Zone not found."
            )

        if not response.ok:

            raise APIRequestError(
                f"HTTP {response.status_code}: "
                f"{response.text}"
            )

        return response.json()

    @staticmethod
    def _parse_datetime(
        value: str,
    ) -> datetime:

        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

    @staticmethod
    def _zone_from_payload(
        payload: dict[str, Any],
    ) -> ZoneData:

        return ZoneData(
            zone_key=payload["zoneKey"],
            zone_name=payload["zoneName"],
            display_name=payload.get(
                "displayName",
                payload["zoneName"],
            ),
            country_name=payload["countryName"],
            country_code=payload["countryCode"],
            parent_zone=payload.get(
                "zoneParentKey",
            ),
            tier=payload["tier"],
            commercially_available=payload[
                "isCommerciallyAvailable"
            ],
        )
    @staticmethod
    def _carbon_from_payload(
        payload: dict[str, Any],
        zone: ZoneData,
    ) -> CarbonIntensityData:
        """
        Convert an API response into a CarbonIntensityData model.
        """

        return CarbonIntensityData(
            zone=zone,
            carbon_intensity=float(
                payload["carbonIntensity"],
            ),
            timestamp=ElectricityMapsClient._parse_datetime(
                payload["datetime"],
            ),
            emission_factor_type=payload.get(
                "emissionFactorType",
                "Forecast",
            ),
            is_estimated=payload.get(
                "isEstimated",
                True,
            ),
            estimation_method=payload.get(
                "estimationMethod",
                "Forecast API",
            ),
            source="Electricity Maps",
        )

    def get_zone(
        self,
        zone: str,
    ) -> ZoneData:
        """
        Retrieve metadata for a single zone.
        """

        payload = self._request(
            "/zone",
            params={
                "zone": zone,
            },
        )

        return self._zone_from_payload(
            payload,
        )

    def get_all_zones(
        self,
    ) -> dict[str, ZoneData]:
        """
        Retrieve all supported Electricity Maps zones.
        """

        payload = self._request(
            "/zones",
        )

        zones: dict[str, ZoneData] = {}

        for zone_key, zone_payload in payload.items():

            zones[zone_key] = (
                self._zone_from_payload(
                    zone_payload,
                )
            )

        return zones

    def get_latest(
        self,
        zone: str,
    ) -> CarbonIntensityData:
        """
        Retrieve the latest carbon intensity for a zone.
        """

        zone_data = self.get_zone(
            zone,
        )

        payload = self._request(
            "/carbon-intensity/latest",
            params={
                "zone": zone,
            },
        )

        return self._carbon_from_payload(
            payload,
            zone_data,
        )

    def get_forecast(
        self,
        zone: str,
    ) -> list[CarbonIntensityData]:
        """
        Retrieve forecast carbon intensity values for a zone.
        """

        zone_data = self.get_zone(
            zone,
        )

        payload = self._request(
            "/carbon-intensity/forecast",
            params={
                "zone": zone,
            },
        )
        forecast = payload.get("forecast")

        if forecast is None:

            raise APIRequestError(
                "Forecast data missing from API response."
            )

        results: list[CarbonIntensityData] = []

        for item in forecast:

            results.append(
                CarbonIntensityData(
                    zone=zone_data,
                    carbon_intensity=float(
                        item["carbonIntensity"],
                    ),
                    timestamp=self._parse_datetime(
                        item["datetime"],
                    ),
                    emission_factor_type="Unknown",
                    is_estimated=False,
                    estimation_method="Not provided by Electricity Maps Forecast API",
                    source="Electricity Maps",
                )
            )
        return results

    def search_zones(
        self,
        query: str,
    ) -> dict[str, ZoneData]:
        """
        Search supported Electricity Maps zones.

        The search is case-insensitive and matches against:

        - Zone key
        - Zone name
        - Display name
        - Country name
        - Country code
        """

        query = query.strip().lower()

        matches: dict[str, ZoneData] = {}
        if self._zones_cache is None:
            self._zones_cache = self.get_all_zones()

        for zone_key, zone in self._zones_cache.items():

            searchable_fields = (
                zone.zone_key,
                zone.zone_name,
                zone.display_name,
                zone.country_name,
                zone.country_code,
            )

            if any(
                query in field.lower()
                for field in searchable_fields
            ):
                matches[zone_key] = zone

        return matches

    def close(
        self,
    ) -> None:
        """
        Close the underlying HTTP session.
        """

        if hasattr(self, "_session"):
            self._session.close()

    def __enter__(
        self,
    ) -> "ElectricityMapsClient":

        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:

        self.close()

    def __del__(self):

        try:
            self.close()
        except Exception:
            pass
    