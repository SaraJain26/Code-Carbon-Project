"""Configuration for the energy smell detection framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from knowledge import RuleCategory


@dataclass(frozen=True)
class DetectorConfiguration:
    """Controls detector framework filtering and future extension behavior."""

    minimum_confidence: float = 0.0
    enabled_categories: frozenset[RuleCategory] | None = None
    enabled_rule_ids: frozenset[str] | None = None
    disabled_rule_ids: frozenset[str] = field(default_factory=frozenset)
    include_experimental_rules: bool = False
    options: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0.0 and 1.0.")
        overlap = (self.enabled_rule_ids or frozenset()) & self.disabled_rule_ids
        if overlap:
            raise ValueError(f"Rules cannot be both enabled and disabled: {sorted(overlap)}")

    def allows_rule(self, rule_id: str, category: RuleCategory, confidence: float) -> bool:
        """Return whether a rule candidate is allowed by this configuration."""

        if confidence < self.minimum_confidence:
            return False
        if self.enabled_rule_ids is not None and rule_id not in self.enabled_rule_ids:
            return False
        if rule_id in self.disabled_rule_ids:
            return False
        if self.enabled_categories is not None and category not in self.enabled_categories:
            return False
        return True
