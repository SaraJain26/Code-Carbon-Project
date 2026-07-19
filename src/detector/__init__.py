"""Energy smell detection framework public API."""

from detector.generators import DefaultFindingGenerator
from detector.evaluators import DefaultRuleEvaluator
from detector.extractors import DefaultCandidateExtractor
from detector.configuration import DetectorConfiguration
from detector.context import DetectionContext
from detector.engine import EnergySmellDetector
from detector.interfaces import CandidateExtractor, Detector, FindingGenerator, RuleEvaluator
from detector.models import Candidate, CandidateEvidence, EnergyFinding, EnergySmellReport, EvidenceKind, ReportStatistics

__all__ = [
    "Candidate",
    "CandidateEvidence",
    "CandidateExtractor",
    "DefaultCandidateExtractor",
    "DefaultFindingGenerator",
    "DefaultRuleEvaluator",
    "DetectionContext",
    "Detector",
    "DetectorConfiguration",
    "EnergyFinding",
    "EnergySmellDetector",
    "EnergySmellReport",
    "EvidenceKind",
    "FindingGenerator",
    "ReportStatistics",
    "RuleEvaluator",
]
