import unittest
from pathlib import Path
from datetime import datetime, timezone

from detector.models import EnergyFinding, EnergySmellReport, ReportStatistics
from knowledge import RuleCategory, RuleConfidence, RuleSeverity
from complexity.models import ComplexityScore, NormalizedComplexityMetrics, RiskLevel
from energy.models import EnergyResult, RuntimeEstimate, EnergyEstimate
from carbon.models import CarbonResult, CarbonEstimate, CarbonIntensityData, ZoneData
from sustainability.metrics import ResearchSustainabilityMetrics


class TestSustainabilityMath(unittest.TestCase):

    def setUp(self):
        # Default mock complexity score
        self.complexity = ComplexityScore(
            structural_complexity_index=0.5,
            carbon_impact_risk_score=0.25,
            risk_level=RiskLevel.MODERATE,
            recommendation="",
            metrics=NormalizedComplexityMetrics(
                cyclomatic_complexity=0.5,
                max_nesting_depth=0.5,
                function_density=0.5,
                energy_smell_score=0.5,
            ),
        )

        # Default mock energy result (18 Joules)
        self.energy_result = EnergyResult(
            runtime=RuntimeEstimate(runtime=1.0),
            energy=EnergyEstimate(energy_joules=18.0),
        )

        # Default mock carbon result (435 gCO2eq/kWh)
        self.carbon_result = CarbonResult(
            energy=self.energy_result,
            carbon=CarbonEstimate(carbon_grams=0.001),
            carbon_data=CarbonIntensityData(
                zone=ZoneData(
                    zone_key="DK-DK1",
                    zone_name="Denmark",
                    display_name="Denmark West",
                    country_name="Denmark",
                    country_code="DK",
                    parent_zone=None,
                    tier="1",
                    commercially_available=True,
                ),
                carbon_intensity=435.0,
                timestamp=datetime.now(timezone.utc),
                emission_factor_type="Measured",
                is_estimated=False,
                estimation_method="API",
                source="Electricity Maps",
            ),
            fallback_used=False,
        )

    def _create_finding(self, rule_id: str, confidence: float) -> EnergyFinding:
        return EnergyFinding.create(
            rule_id=rule_id,
            severity=RuleSeverity.HIGH,
            confidence=RuleConfidence(confidence),
            source_file=Path("test.py"),
            line_number=1,
            end_line=1,
            message="Test message",
            explanation="Test explanation",
            evidence=[],
            recommendation="Test recommendation",
            category=RuleCategory.COMPUTATION,
        )

    def test_boundary_conditions_ess(self):
        # 1. Zero smells boundary: ESS must be exactly 0.0
        report_empty = EnergySmellReport.from_findings([], "0.1.0")
        ess_empty = ResearchSustainabilityMetrics.compute_energy_smell_score(report_empty)
        self.assertEqual(ess_empty, 0.0)

        # 2. Maximum confidence boundary: ESS must be exactly 10.0
        finding_max = self._create_finding("EKB-COMP-001", 1.0)
        report_max = EnergySmellReport.from_findings([finding_max], "0.1.0")
        ess_max = ResearchSustainabilityMetrics.compute_energy_smell_score(report_max)
        self.assertEqual(ess_max, 10.0)

        # 3. Floating-point clamp behavior: confidence in [0, 1]
        finding_half = self._create_finding("EKB-COMP-001", 0.5)
        report_half = EnergySmellReport.from_findings([finding_half], "0.1.0")
        ess_half = ResearchSustainabilityMetrics.compute_energy_smell_score(report_half)
        self.assertEqual(ess_half, 5.0)

    def test_boundary_conditions_cirs(self):
        # 1. Zero hazard boundary (Energy = 0.0) -> CIRS = 0.0
        zero_energy = EnergyResult(
            runtime=RuntimeEstimate(runtime=0.0),
            energy=EnergyEstimate(energy_joules=0.0)
        )
        cirs_zero_energy = ResearchSustainabilityMetrics.compute_carbon_impact_risk_score(
            self.complexity, zero_energy, self.carbon_result, 5.0
        )
        self.assertEqual(cirs_zero_energy, 0.0)

        # 2. Zero hazard boundary (Carbon Intensity = 0.0) -> CIRS = 0.0
        zero_carbon_data = CarbonResult(
            energy=self.energy_result,
            carbon=CarbonEstimate(carbon_grams=0.0),
            carbon_data=CarbonIntensityData(
                zone=self.carbon_result.carbon_data.zone,
                carbon_intensity=0.0,
                timestamp=datetime.now(timezone.utc),
                emission_factor_type="Measured",
                is_estimated=False,
                estimation_method="API",
                source="API"
            ),
            fallback_used=False
        )
        cirs_zero_carbon = ResearchSustainabilityMetrics.compute_carbon_impact_risk_score(
            self.complexity, self.energy_result, zero_carbon_data, 5.0
        )
        self.assertEqual(cirs_zero_carbon, 0.0)

    def test_monotonicity_ess(self):
        # Adding more smells must monotonically increase or keep ESS constant
        findings = []
        last_ess = 0.0

        for i in range(1, 10):
            findings.append(self._create_finding(f"EKB-COMP-00{i}", 0.2))
            report = EnergySmellReport.from_findings(findings, "0.1.0")
            current_ess = ResearchSustainabilityMetrics.compute_energy_smell_score(report)
            
            # Monotonicity check: ESS(n) > ESS(n-1) when adding non-zero confidence smells
            self.assertGreater(current_ess, last_ess)
            last_ess = current_ess

    def test_monotonicity_cirs(self):
        # CIRS_Research must monotonically increase with respect to energy
        cirs_1 = ResearchSustainabilityMetrics.compute_carbon_impact_risk_score(
            self.complexity, self.energy_result, self.carbon_result, 5.0
        )

        higher_energy = EnergyResult(
            runtime=RuntimeEstimate(runtime=2.0),
            energy=EnergyEstimate(energy_joules=100.0)
        )
        cirs_2 = ResearchSustainabilityMetrics.compute_carbon_impact_risk_score(
            self.complexity, higher_energy, self.carbon_result, 5.0
        )
        self.assertGreater(cirs_2, cirs_1)

        # CIRS_Research must monotonically increase with respect to ESS
        cirs_3 = ResearchSustainabilityMetrics.compute_carbon_impact_risk_score(
            self.complexity, self.energy_result, self.carbon_result, 8.0
        )
        self.assertGreater(cirs_3, cirs_1)

    def test_sensitivity_analysis(self):
        # Sensitivity: a change in input confidence must result in a continuous change in output ESS
        finding = self._create_finding("EKB-COMP-001", 0.5)
        report_base = EnergySmellReport.from_findings([finding], "0.1.0")
        ess_base = ResearchSustainabilityMetrics.compute_energy_smell_score(report_base)

        # Perturb confidence by +0.01
        finding_perturbed = self._create_finding("EKB-COMP-001", 0.51)
        report_pert = EnergySmellReport.from_findings([finding_perturbed], "0.1.0")
        ess_pert = ResearchSustainabilityMetrics.compute_energy_smell_score(report_pert)

        diff = ess_pert - ess_base
        # Difference should match the scaled perturbation exactly (0.01 * 10 = 0.1)
        self.assertAlmostEqual(diff, 0.1)

    def test_ablation_study(self):
        # Verify impact when sub-detector findings are ablated (removed)
        f1 = self._create_finding("EKB-COMP-001", 0.8)
        f2 = self._create_finding("EKB-IO-001", 0.7)
        
        report_both = EnergySmellReport.from_findings([f1, f2], "0.1.0")
        ess_both = ResearchSustainabilityMetrics.compute_energy_smell_score(report_both)

        # Ablate detector f2 (remove f2)
        report_ablated = EnergySmellReport.from_findings([f1], "0.1.0")
        ess_ablated = ResearchSustainabilityMetrics.compute_energy_smell_score(report_ablated)

        # Ablated score should be lower than combined score
        self.assertLess(ess_ablated, ess_both)
        # Remaining score is exactly f1 membership scaled (8.0)
        self.assertEqual(ess_ablated, 8.0)


if __name__ == "__main__":
    unittest.main()
