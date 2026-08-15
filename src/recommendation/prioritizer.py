"""
Prioritizer logic for the Recommendation Engine.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from detector.models import EnergyFinding
    from complexity.models import ComplexityScore
    from energy.models import EnergyResult
    from carbon.models import CarbonResult


class RecommendationPrioritizer:
    """
    Computes priority scores for recommendations based on physical risk exposure.
    """

    def compute_rule_priority(
        self,
        findings: list[EnergyFinding],
        complexity: ComplexityScore,
        energy_result: EnergyResult | None,
        carbon_result: CarbonResult | None,
    ) -> float:
        """
        Compute the priority score of a rule using Hazard and Exposure.
        
        Formula:
            Priority = Hazard * Exposure_rule
                     = (Energy * Intensity) * SCI * P_leak_rule
        """
        if not findings:
            return 0.0

        # Calculate P_leak for this specific rule's findings
        # using the algebraic t-conorm possibility union
        product = 1.0
        for finding in findings:
            confidence_val = finding.confidence.value
            product *= (1.0 - confidence_val)
        p_leak_rule = 1.0 - product

        # Base structural complexity index (SCI)
        sci = complexity.structural_complexity_index

        # Grid intensity (I) in gCO2eq/kWh, and Energy (E) in kWh
        energy_kwh = 0.0
        intensity = 0.0

        if energy_result is not None:
            # 1 Joule = 2.77778e-7 kWh (or joules / 3.6e6)
            energy_kwh = energy_result.energy.energy_joules / 3_600_000.0

        if carbon_result is not None:
            intensity = carbon_result.carbon_data.carbon_intensity

        hazard = energy_kwh * intensity

        # Multiplicative exposure risk score
        priority = hazard * sci * p_leak_rule

        # If energy or carbon result is not available, fallback to structural exposure
        if math.isclose(priority, 0.0):
            priority = sci * p_leak_rule

        return float(priority)
