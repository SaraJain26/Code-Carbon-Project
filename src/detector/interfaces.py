"""Abstract interfaces for the energy smell detection framework."""

from __future__ import annotations

from abc import ABC, abstractmethod

from detector.context import DetectionContext
from detector.models import Candidate, EnergyFinding, EnergySmellReport


class CandidateExtractor(ABC):
    """Extract candidate rule matches from the analysis result."""

    @abstractmethod
    def extract(self, context: DetectionContext) -> list[Candidate]:
        """Return possible rule candidates."""
        raise NotImplementedError


class RuleEvaluator(ABC):
    """Evaluate extracted candidates."""

    @abstractmethod
    def evaluate(
        self,
        candidates: list[Candidate],
        context: DetectionContext,
    ) -> list[Candidate]:
        """
        Evaluate candidates.

        This phase may filter, enrich or modify candidate confidence.
        It MUST NOT generate EnergyFinding objects.
        """
        raise NotImplementedError


class ConfidenceScorer(ABC):
    """Assign or adjust confidence for evaluated candidates."""

    @abstractmethod
    def score(
        self,
        candidates: list[Candidate],
        context: DetectionContext,
    ) -> list[Candidate]:
        """Return scored candidates."""
        raise NotImplementedError


class FindingGenerator(ABC):
    """Convert evaluated candidates into final findings."""

    @abstractmethod
    def generate(
        self,
        candidates: list[Candidate],
        context: DetectionContext,
    ) -> list[EnergyFinding]:
        """Generate detector findings."""
        raise NotImplementedError


class Detector(ABC):
    """High-level detector interface."""

    @abstractmethod
    def detect(
        self,
        context: DetectionContext,
    ) -> EnergySmellReport:
        """Run the detector pipeline."""
        raise NotImplementedError