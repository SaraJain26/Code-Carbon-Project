"""
Version 1 (Research Prototype) Sustainability Metrics.

This package computes the research-validated Energy Smell Score (ESS)
and Carbon Impact Risk Score (CIRS) using fuzzy possibility aggregation
and environmental hazard exposure models.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from detector.models import EnergySmellReport
    from complexity.models import ComplexityScore
    from energy.models import EnergyResult
    from carbon.models import CarbonResult


class ResearchSustainabilityMetrics:
    """
    Computes Version 1 (Research Prototype) sustainability metrics:
    - Energy Smell Score (ESS) using Fuzzy Set Belief Union.
    - Carbon Impact Risk Score (CIRS) using Proportional Risk Exposure.
    """

    @staticmethod
    def compute_energy_smell_score(report: EnergySmellReport) -> float:
        """
        Compute the expected active code energy leak score (ESS).
        
        Formula:
            ESS = 10.0 * P_leak
            P_leak = 1.0 - PROD_{f in F} (1.0 - c_f)
            
        Where:
            c_f: The detection confidence of smell finding f.
            P_leak: Fuzzy joint possibility of at least one active leak.
            
        Classification of Components:
        1. Mathematically Derived Components:
           - Algebraic t-conorm operator (Klement et al., 2000; Dubois & Prade, 1985).
        2. Assumptions:
           - Energy smells behave as independent possibility indicators.
           - Confidence c_f represents the fuzzy belief of a leak being active.
        3. Engineering Approximations:
           - Scaling factor of 10.0 is used to map P_leak to the stable normalizer's range.
        4. Limitations:
           - Does not model co-occurrence interaction dependencies between smells.
        """
        if not report.findings:
            return 0.0

        product = 1.0
        for finding in report.findings:
            confidence_val = finding.confidence.value
            product *= (1.0 - confidence_val)

        p_leak = 1.0 - product
        
        # Scale to [0.0, 10.0] to conform with ComplexityNormalizer.MAX_ENERGY_SMELL_SCORE
        ess = 10.0 * p_leak
        return float(ess)

    @staticmethod
    def compute_carbon_impact_risk_score(
        complexity: ComplexityScore,
        energy_result: EnergyResult,
        carbon_result: CarbonResult,
        ess: float,
    ) -> float:
        """
        Compute the physical Carbon Impact Risk Score (CIRS_Research) in effective gCO2eq/run.
        
        Formula:
            CIRS_Research = Hazard * Exposure
            Hazard (H) = E * I  (grams of CO2eq per run)
            Exposure (Ex) = SCI * (1.0 + P_leak)
            
            Therefore:
            CIRS_Research = (E * I) * SCI * (1.0 + (ESS / 10.0))
            
        Where:
            E: Predicted energy consumption in kWh (joules / 3,600,000).
            I: Location-based marginal carbon intensity in gCO2eq/kWh.
            SCI: Structural Complexity Index (0.0 to 1.0).
            ESS: Energy Smell Score (0.0 to 10.0).
            P_leak: ESS / 10.0.
            
        Classification of Components:
        1. Mathematically Derived Components:
           - Carbon footprint H = E * I (Green Software Foundation SCI Specification, 2022).
           - Risk = Hazard * Exposure (ISO 31000 / ISO/IEC Guide 73:2009).
        2. Assumptions:
           - Physical carbon footprint scales linearly with energy and intensity.
           - Structural complexity and smell presence amplify the risk exposure.
        3. Engineering Approximations:
           - Linear exposure degradation model of (1.0 + P_leak) scales the impact up to 2.0x.
        4. Limitations:
           - Static estimation cannot capture dynamic execution path variations.
        """
        # Hazard: physical carbon footprint of a single run in grams of CO2eq
        # Convert energy from Joules to kWh (1 Joule = 1 / 3.6e6 kWh)
        energy_kwh = energy_result.energy.energy_joules / 3_600_000.0
        intensity = carbon_result.carbon_data.carbon_intensity
        hazard = energy_kwh * intensity

        # Exposure: structural index scaled by smell possibility
        sci = complexity.structural_complexity_index
        p_leak = ess / 10.0
        exposure = sci * (1.0 + p_leak)

        # Multiplicative risk
        cirs = hazard * exposure
        return float(cirs)
