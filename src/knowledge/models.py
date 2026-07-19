"""Typed models for the Energy Knowledge Base."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RuleSeverity(str, Enum):
    """Relative importance of an energy rule."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RuleCategory(str, Enum):
    """Energy-smell taxonomy categories used by the EKB."""

    COMPUTATION = "computation"
    IO = "io"
    NETWORK = "network"
    CONCURRENCY = "concurrency"
    MEMORY = "memory"
    CONTROL_FLOW = "control_flow"
    EXCEPTION_HANDLING = "exception_handling"
    ASYNC = "async"


@dataclass(frozen=True)
class RuleConfidence:
    """Confidence assigned to a rule, from 0.0 to 1.0."""

    value: float
    rationale: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            raise ValueError("Rule confidence must be between 0.0 and 1.0.")


@dataclass(frozen=True, order=True)
class RuleVersion:
    """Semantic version for one rule definition."""

    major: int
    minor: int
    patch: int = 0

    @classmethod
    def parse(cls, value: str) -> "RuleVersion":
        """Parse a semantic version string."""

        parts = value.split(".")
        if len(parts) not in {2, 3}:
            raise ValueError(f"Invalid rule version '{value}'. Expected MAJOR.MINOR[.PATCH].")
        try:
            numbers = [int(part) for part in parts]
        except ValueError as exc:
            raise ValueError(f"Invalid rule version '{value}'. Version parts must be integers.") from exc
        if any(number < 0 for number in numbers):
            raise ValueError(f"Invalid rule version '{value}'. Version parts must be non-negative.")
        if len(numbers) == 2:
            numbers.append(0)
        return cls(*numbers)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class RuleReference:
    """Literature, documentation, or empirical source supporting a rule."""

    title: str
    url: str | None = None
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    doi: str | None = None


@dataclass(frozen=True)
class EnergyRule:
    """One language-independent energy knowledge rule."""

    id: str
    name: str
    description: str
    category: RuleCategory
    severity: RuleSeverity
    confidence: RuleConfidence
    rationale: str
    detection: str
    recommendation: str
    references: list[RuleReference]
    version: RuleVersion
    tags: frozenset[str] = field(default_factory=frozenset)
    languages: frozenset[str] = field(default_factory=lambda: frozenset({"any"}))
