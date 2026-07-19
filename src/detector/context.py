"""Detection context shared across detector pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from analysis.models import AnalysisResult
from detector.configuration import DetectorConfiguration
from knowledge import RuleRepository


@dataclass(frozen=True)
class DetectionContext:
    """Immutable inputs required by detector framework stages."""

    analysis_result: AnalysisResult
    rule_repository: RuleRepository
    configuration: DetectorConfiguration = field(default_factory=DetectorConfiguration)
    metadata: dict[str, Any] = field(default_factory=dict)
