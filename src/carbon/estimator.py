"""
Predictive carbon estimation.

This module estimates software carbon emissions using the
estimated software energy and the electricity carbon intensity.

Model

    Carbon = Energy × Carbon Intensity

where

    Energy is expressed in kWh

    Carbon Intensity is expressed in gCO₂e/kWh

The resulting carbon estimate is expressed in grams of CO₂-equivalent.
"""

from __future__ import annotations

from .models import CarbonEstimate


class CarbonEstimator:
    """
    Estimates software carbon emissions.
    """

    def estimate(
        self,
        energy_kwh: float,
        carbon_intensity: float,
    ) -> CarbonEstimate:
        """
        Estimate software carbon emissions.

        Parameters
        ----------
        energy_kwh
            Estimated software energy (kWh).

        carbon_intensity
            Electricity carbon intensity
            (gCO₂e/kWh).

        Returns
        -------
        CarbonEstimate
        """

        carbon = (
            energy_kwh
            * carbon_intensity
        )

        return CarbonEstimate(
            carbon_grams=round(
                carbon,
                8,
            ),
        )