"""In-memory Energy Knowledge Base repository."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator

from knowledge.models import EnergyRule, RuleCategory, RuleSeverity
from knowledge.validation import RuleValidationError


class RuleRepository:
    """Queryable in-memory repository of energy rules."""

    def __init__(self, rules: Iterable[EnergyRule]) -> None:
        self._rules_by_id: dict[str, EnergyRule] = {}
        self._by_category: dict[RuleCategory, list[EnergyRule]] = defaultdict(list)
        self._by_severity: dict[RuleSeverity, list[EnergyRule]] = defaultdict(list)
        self._by_tag: dict[str, list[EnergyRule]] = defaultdict(list)

        duplicates: list[str] = []
        for rule in rules:
            if rule.id in self._rules_by_id:
                duplicates.append(rule.id)
                continue
            self._rules_by_id[rule.id] = rule
            self._by_category[rule.category].append(rule)
            self._by_severity[rule.severity].append(rule)
            for tag in rule.tags:
                self._by_tag[tag].append(rule)
        if duplicates:
            raise RuleValidationError([f"Duplicate rule id '{rule_id}'." for rule_id in sorted(set(duplicates))])

    def get(self, rule_id: str) -> EnergyRule | None:
        """Return a rule by ID, or `None` when absent."""

        return self._rules_by_id.get(rule_id)

    def require(self, rule_id: str) -> EnergyRule:
        """Return a rule by ID or raise a clear lookup error."""

        rule = self.get(rule_id)
        if rule is None:
            raise KeyError(f"Unknown energy rule id '{rule_id}'.")
        return rule

    def by_category(self, category: RuleCategory) -> list[EnergyRule]:
        """Return all rules in one category."""

        return list(self._by_category.get(category, []))

    def by_severity(self, severity: RuleSeverity) -> list[EnergyRule]:
        """Return all rules with one severity."""

        return list(self._by_severity.get(severity, []))

    def by_tag(self, tag: str) -> list[EnergyRule]:
        """Return all rules containing a tag."""

        return list(self._by_tag.get(tag, []))

    def all(self) -> list[EnergyRule]:
        """Return all rules in insertion order."""

        return list(self._rules_by_id.values())

    def __iter__(self) -> Iterator[EnergyRule]:
        return iter(self._rules_by_id.values())

    def __len__(self) -> int:
        return len(self._rules_by_id)
