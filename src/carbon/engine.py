"""
Carbon estimation engine.

Coordinates the complete carbon estimation pipeline.
"""

from __future__ import annotations

from datetime import datetime, timezone

from energy.models import EnergyResult

from .api import (
    APIRequestError,
    AuthenticationError,
    InvalidZoneError,
)
from .providers import CarbonIntensityProvider
from .config import (
    DEFAULT_GLOBAL_CARBON_INTENSITY,
    DEFAULT_GLOBAL_CARBON_INTENSITY_SOURCE,
)
from .converter import EnergyUnitConverter
from .estimator import CarbonEstimator
from .models import (
    CarbonIntensityData,
    CarbonResult,
    ZoneData,
)


class CarbonEstimationEngine:
    """
    End-to-end carbon estimation engine.
    """

    def __init__(
        self,
        client: CarbonIntensityProvider,
    ) -> None:

        self._client = client
        self._converter = EnergyUnitConverter()
        self._estimator = CarbonEstimator()

    def analyze(
        self,
        energy_result: EnergyResult,
        *,
        zone: str,
        use_global_average: bool = False,
    ) -> CarbonResult:
        """
        Estimate software carbon emissions using the
        latest regional carbon intensity.
        """

        try:

            carbon_data = self._client.get_latest(
                zone,
            )

            fallback_used = False

        except (
            AuthenticationError,
            InvalidZoneError,
            APIRequestError,
            Exception,
        ) as exc:

            import logging
            logging.getLogger(__name__).warning(
                "Electricity Maps API call failed: %s. Using fallback intensity.",
                str(exc)
            )

            if not use_global_average:
                raise

            carbon_data = CarbonIntensityData(
                zone=ZoneData(
                    zone_key="GLOBAL",
                    zone_name="Global Average",
                    display_name="Global Average",
                    country_name="Global",
                    country_code="GL",
                    parent_zone=None,
                    tier="N/A",
                    commercially_available=True,
                ),
                carbon_intensity=DEFAULT_GLOBAL_CARBON_INTENSITY,
                timestamp=datetime.now(
                    timezone.utc,
                ),
                emission_factor_type="Global Average",
                is_estimated=True,
                estimation_method="Fallback",
                source=DEFAULT_GLOBAL_CARBON_INTENSITY_SOURCE,
            )

            fallback_used = True

        energy_kwh = self._converter.joules_to_kwh(
            energy_result.energy,
        )

        carbon = self._estimator.estimate(
            energy_kwh,
            carbon_data.carbon_intensity,
        )

        return CarbonResult(
            energy=energy_result,
            carbon=carbon,
            carbon_data=carbon_data,
            fallback_used=fallback_used,
        )

    def forecast(
        self,
        energy_result: EnergyResult,
        *,
        zone: str,
    ) -> list[CarbonResult]:
        """
        Estimate carbon emissions using forecast
        carbon intensity values.
        """

        forecasts = self._client.get_forecast(
            zone,
        )

        energy_kwh = self._converter.joules_to_kwh(
            energy_result.energy,
        )

        results: list[CarbonResult] = []

        for carbon_data in forecasts:

            carbon = self._estimator.estimate(
                energy_kwh,
                carbon_data.carbon_intensity,
            )

            results.append(
                CarbonResult(
                    energy=energy_result,
                    carbon=carbon,
                    carbon_data=carbon_data,
                    fallback_used=False,
                )
            )

        return results

    @staticmethod
    def best_execution_window(
        forecasts: list[CarbonResult],
    ) -> CarbonResult:
        """
        Return the forecast corresponding to the
        minimum carbon intensity.
        """

        if not forecasts:

            raise ValueError(
                "Forecast list cannot be empty."
            )

        return min(
            forecasts,
            key=lambda result: (
                result.carbon_data.carbon_intensity
            ),
        )

    @staticmethod
    def percentage_reduction(
        current: CarbonResult,
        recommended: CarbonResult,
    ) -> float:
        """
        Compute the percentage reduction in carbon
        intensity between the current estimate and
        the recommended execution window.
        """

        current_ci = (
            current.carbon_data.carbon_intensity
        )

        recommended_ci = (
            recommended.carbon_data.carbon_intensity
        )

        if current_ci == 0:

            return 0.0

        return (
            (
                current_ci - recommended_ci
            )
            / current_ci
        ) * 100.0