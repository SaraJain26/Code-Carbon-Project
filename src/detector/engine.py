"""Generic detector pipeline implementation."""

from __future__ import annotations

from detector.context import DetectionContext
from detector.interfaces import (
    CandidateExtractor,
    ConfidenceScorer,
    Detector,
    FindingGenerator,
    RuleEvaluator,
)
from detector.models import EnergySmellReport


class EnergySmellDetector(Detector):
    """
    Generic detector pipeline.

    This class orchestrates the pipeline only.

    It deliberately contains NO smell detection logic.
    """

    VERSION = "0.1.0"

    def __init__(
        self,
        extractor: CandidateExtractor,
        evaluator: RuleEvaluator,
        scorer: ConfidenceScorer,
        generator: FindingGenerator,
    ) -> None:
        self._extractor = extractor
        self._evaluator = evaluator
        self._scorer = scorer
        self._generator = generator

    @property
    def version(self) -> str:
        return self.VERSION

    def detect(
        self,
        context: DetectionContext,
    ) -> EnergySmellReport:

        candidates = self._extractor.extract(context)

        evaluated = self._evaluator.evaluate(
            candidates,
            context,
        )

        scored = self._scorer.score(
            evaluated,
            context,
        )

        findings = self._generator.generate(
            scored,
            context,
        )

        return EnergySmellReport.from_findings(
            findings=findings,
            detector_version=self.version,
        )