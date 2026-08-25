"""
End-to-end predictive software carbon estimation pipeline.
"""

from __future__ import annotations

from pathlib import Path

from analysis import StaticAnalysisEngine
from analysis.models import AnalysisResult

from detector import (
    DefaultCandidateExtractor,
    DefaultConfidenceScorer,
    DefaultFindingGenerator,
    DefaultRuleEvaluator,
    DetectionContext,
    DetectorConfiguration,
    EnergySmellDetector,
)
from detector.models import EnergySmellReport

from complexity.engine import ComplexityEngine
from complexity.metrics import ComplexityMetricsExtractor
from complexity.models import ComplexityMetrics, ComplexityScore

from hardware_profile import HardwareProfilingEngine
from hardware_profile.models import HardwareProfile, HardwareScore

from energy import EnergyEstimationEngine
from energy.models import EnergyResult 

from carbon import (
    CarbonEstimationEngine,
    get_carbon_provider,
)

from knowledge import (
    RuleLoader,
    RuleRepository,
)


class PredictivePipeline:
    """
    Executes the complete predictive carbon estimation workflow.
    """

    def __init__(self) -> None:

        self._analysis_engine = StaticAnalysisEngine()

        self._complexity_extractor = (
            ComplexityMetricsExtractor()
        )

        self._complexity_engine = (
            ComplexityEngine()
        )

        self._hardware_engine = (
            HardwareProfilingEngine()
        )

        self._energy_engine = (
            EnergyEstimationEngine()
        )

        self._carbon_engine = (
            CarbonEstimationEngine(
                get_carbon_provider(),
            )
        )

        loader = RuleLoader()

        rules = loader.load_default_rules()

        repository = RuleRepository(
            rules,
        )

        configuration = DetectorConfiguration()

        self._detector = EnergySmellDetector(
            extractor=DefaultCandidateExtractor(),
            evaluator=DefaultRuleEvaluator(),
            scorer=DefaultConfidenceScorer(),
            generator=DefaultFindingGenerator(),
        )

        self._repository = repository

        self._configuration = configuration


    def _analysis(
        self,
        source_file: str | Path,
    ) -> AnalysisResult:

        return self._analysis_engine.analyze_file(
            source_file,
        )


    def _detect(
        self,
        analysis_result: AnalysisResult,
    ) -> EnergySmellReport:

        context = DetectionContext(
            analysis_result=analysis_result,
            rule_repository=self._repository,
            configuration=self._configuration,
        )

        return self._detector.detect(
            context,
        )

    
    def run(
        self,
        source_file: str | Path,
        *,
        zone: str,
        use_global_average: bool = False,
    ) -> dict[str, object]:

        analysis_result = self._analysis(
            source_file,
        )

        smell_report = self._detect(
            analysis_result,
        )

        #
        # Week 8 placeholder.
        #
        # ESS integration will be added later.
        #
        energy_smell_score = 0.0

        complexity_metrics: ComplexityMetrics = (
            self._complexity_extractor.extract(
                analysis_result,
                energy_smell_score,
            )
        )

        complexity_score: ComplexityScore = (
            self._complexity_engine.analyze(
                complexity_metrics,
            )
        )

        (
            hardware_profile,
            _normalized_profile,
            hardware_score,
        ) = self._hardware_engine.analyze()
        hardware_profile: HardwareProfile
        hardware_score: HardwareScore

        energy_result: EnergyResult = (
            self._energy_engine.analyze(
                complexity_score,
                hardware_score,
            )
        )

        carbon_result = (
            self._carbon_engine.analyze(
                energy_result,
                zone=zone,
                use_global_average=(
                    use_global_average
                ),
            )
        )

        return {
            "analysis": analysis_result,
            "energy_smell_report": smell_report,
            "complexity_metrics": complexity_metrics,
            "complexity_score": complexity_score,
            "hardware_profile": hardware_profile,
            "hardware_score": hardware_score,
            "energy_result": energy_result,
            "carbon_result": carbon_result,
        }
__all__ = [
    "PredictivePipeline",
]