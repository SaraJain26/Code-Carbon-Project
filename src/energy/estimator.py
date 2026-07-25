"""
Predictive energy estimation.

This module estimates the relative energy consumption of a program
using the estimated runtime and the Reference Compute Power (RCP).

Model:

    Energy = Runtime × RCP

where

    Runtime = SCI / HPI

The estimated energy is expressed in reference Joules
(Watt-seconds). It is intended for relative comparison
rather than exact physical measurement.
"""

from __future__ import annotations

from hardware_profile.models import HardwareScore

from .models import EnergyEstimate, RuntimeEstimate


class EnergyEstimator:
    """
    Estimates software energy consumption.
    """

    def estimate(
        self,
        runtime: RuntimeEstimate,
        hardware: HardwareScore,
    ) -> EnergyEstimate:
        """
        Estimate software energy consumption.

        Parameters
        ----------
        runtime
            Estimated runtime.

        hardware
            Hardware profiling output.

        Returns
        -------
        EnergyEstimate
        """

        energy = (
            runtime.runtime
            * hardware.reference_compute_power_w
        )

        return EnergyEstimate(
            energy_joules=round(
                energy,
                4,
            ),
        )