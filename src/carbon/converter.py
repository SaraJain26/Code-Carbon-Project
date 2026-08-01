"""
Unit conversion utilities for carbon estimation.

This module converts estimated software energy from Joules to
kilowatt-hours (kWh), which is the standard unit required for
carbon-emission estimation.

Relationship

    1 kWh = 3.6 × 10⁶ Joules
"""

from __future__ import annotations

from energy.models import EnergyEstimate


class EnergyUnitConverter:
    """
    Converts energy units.
    """

    JOULES_PER_KWH = 3_600_000.0

    def joules_to_kwh(
        self,
        energy: EnergyEstimate,
    ) -> float:
        """
        Convert Joules to kilowatt-hours.

        Parameters
        ----------
        energy
            Estimated software energy.

        Returns
        -------
        float
            Energy in kWh.
        """

        return (
            energy.energy_joules
            / self.JOULES_PER_KWH
        )