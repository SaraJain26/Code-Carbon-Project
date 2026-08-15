import unittest
from datetime import datetime, timezone
from pathlib import Path

from detector.models import EnergyFinding, EnergySmellReport, ReportStatistics
from knowledge import RuleCategory, RuleConfidence, RuleSeverity
from complexity.models import ComplexityScore, NormalizedComplexityMetrics, RiskLevel
from energy.models import EnergyResult, RuntimeEstimate, EnergyEstimate
from carbon.models import CarbonResult, CarbonEstimate, CarbonIntensityData, ZoneData
from recommendation.engine import RecommendationEngine


class TestRecommendationEngine(unittest.TestCase):

    def setUp(self):
        self.engine = RecommendationEngine()

        # Create mock complexity score
        self.complexity = ComplexityScore(
            structural_complexity_index=0.80,
            carbon_impact_risk_score=0.60,
            risk_level=RiskLevel.MODERATE,
            recommendation="",
            metrics=NormalizedComplexityMetrics(
                cyclomatic_complexity=0.8,
                max_nesting_depth=0.6,
                function_density=0.4,
                energy_smell_score=0.5,
            ),
        )

        # Create mock energy result
        self.energy_result = EnergyResult(
            runtime=RuntimeEstimate(runtime=2.0),
            energy=EnergyEstimate(energy_joules=90.0),
        )

        # Create mock carbon result
        self.carbon_result = CarbonResult(
            energy=self.energy_result,
            carbon=CarbonEstimate(carbon_grams=0.01),
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
                carbon_intensity=250.0,
                timestamp=datetime.now(timezone.utc),
                emission_factor_type="Measured",
                is_estimated=False,
                estimation_method="API",
                source="Electricity Maps",
            ),
            fallback_used=False,
        )

    def test_empty_findings(self):
        report = EnergySmellReport(
            findings=[],
            summary=ReportStatistics(0, {}, {}, 0.0),
            generated_at=datetime.now(timezone.utc),
            detector_version="0.1.0",
        )
        rec_report = self.engine.generate(
            smell_report=report,
            complexity=self.complexity,
            energy_result=self.energy_result,
            carbon_result=self.carbon_result,
        )
        self.assertEqual(len(rec_report.recommendations), 0)
        self.assertIn("No energy smells detected", rec_report.summary)

    def test_recommendation_prioritization(self):
        # Create two findings for different rules
        finding_nested_loop = EnergyFinding.create(
            rule_id="EKB-COMP-001",
            severity=RuleSeverity.HIGH,
            confidence=RuleConfidence(0.9),
            source_file=Path("test.py"),
            line_number=10,
            end_line=15,
            message="Nested loops detected",
            explanation="",
            evidence=[],
            recommendation="",
            category=RuleCategory.COMPUTATION,
        )

        finding_file_io = EnergyFinding.create(
            rule_id="EKB-IO-001",
            severity=RuleSeverity.HIGH,
            confidence=RuleConfidence(0.6),  # Lower confidence
            source_file=Path("test.py"),
            line_number=20,
            end_line=22,
            message="File IO inside loop",
            explanation="",
            evidence=[],
            recommendation="",
            category=RuleCategory.IO,
        )

        report = EnergySmellReport.from_findings(
            findings=[finding_nested_loop, finding_file_io],
            detector_version="0.1.0",
        )

        rec_report = self.engine.generate(
            smell_report=report,
            complexity=self.complexity,
            energy_result=self.energy_result,
            carbon_result=self.carbon_result,
        )

        self.assertEqual(len(rec_report.recommendations), 2)
        # EKB-COMP-001 has higher confidence (0.9 vs 0.6) and should be first
        self.assertEqual(rec_report.recommendations[0].rule_id, "EKB-COMP-001")
        self.assertEqual(rec_report.recommendations[1].rule_id, "EKB-IO-001")

        # Verify that priority score calculations are strictly positive and float
        self.assertGreater(rec_report.recommendations[0].priority_score, 0.0)
        self.assertIsInstance(rec_report.recommendations[0].priority_score, float)

        # Check references and code example are present
        self.assertIsNotNone(rec_report.recommendations[0].code_example)
        self.assertIn("Flatten or Vectorize Nested Loops", rec_report.recommendations[0].title)


if __name__ == "__main__":
    unittest.main()
