"""YAML loader and validator for Energy Knowledge Base rules."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from knowledge.models import (
    EnergyRule,
    RuleCategory,
    RuleConfidence,
    RuleReference,
    RuleSeverity,
    RuleVersion,
)
from knowledge.validation import RuleValidationError, require_list, require_mapping


class RuleLoader:
    """Loads and validates EKB YAML rule files."""

    REQUIRED_RULE_FIELDS = frozenset(
        {
            "id",
            "name",
            "description",
            "category",
            "severity",
            "confidence",
            "rationale",
            "detection",
            "recommendation",
            "references",
            "version",
            "tags",
        }
    )

    def load_default_rules(self) -> list[EnergyRule]:
        """Load the bundled Phase 3 energy rule collection."""

        rule_path = resources.files("knowledge.rules").joinpath("energy_rules.yaml")
        with resources.as_file(rule_path) as path:
            return self.load_files([path])

    def load_file(self, path: str | Path) -> list[EnergyRule]:
        """Load rules from one YAML file."""

        return self.load_files([path])

    def load_files(self, paths: list[str | Path]) -> list[EnergyRule]:
        """Load rules from multiple YAML files and validate duplicate IDs."""

        rules: list[EnergyRule] = []
        errors: list[str] = []
        for path_value in paths:
            path = Path(path_value)
            try:
                rules.extend(self._load_one(path))
            except RuleValidationError as exc:
                errors.extend(f"{path}: {message}" for message in exc.messages)
        errors.extend(self._duplicate_id_errors(rules))
        if errors:
            raise RuleValidationError(errors)
        return rules

    def _load_one(self, path: Path) -> list[EnergyRule]:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise RuleValidationError([f"Malformed YAML: {exc}"]) from exc
        except OSError as exc:
            raise RuleValidationError([f"Unable to read rule file: {exc}"]) from exc

        document = require_mapping(raw, "Rule file")
        raw_rules = require_list(document.get("rules"), "rules")
        parsed: list[EnergyRule] = []
        errors: list[str] = []
        for index, raw_rule in enumerate(raw_rules):
            try:
                parsed.append(self._parse_rule(require_mapping(raw_rule, f"rules[{index}]"), index))
            except RuleValidationError as exc:
                errors.extend(exc.messages)
        if errors:
            raise RuleValidationError(errors)
        return parsed

    def _parse_rule(self, raw: dict[str, Any], index: int) -> EnergyRule:
        context = f"rules[{index}]"
        errors = self._missing_field_errors(raw, context)
        if errors:
            raise RuleValidationError(errors)

        try:
            category = RuleCategory(raw["category"])
        except ValueError:
            errors.append(f"{context}.category has invalid value '{raw.get('category')}'.")
            category = RuleCategory.COMPUTATION

        try:
            severity = RuleSeverity(raw["severity"])
        except ValueError:
            errors.append(f"{context}.severity has invalid value '{raw.get('severity')}'.")
            severity = RuleSeverity.INFO

        confidence = self._parse_confidence(raw["confidence"], context, errors)
        version = self._parse_version(raw["version"], context, errors)
        references = self._parse_references(raw["references"], context, errors)
        tags = self._parse_string_set(raw.get("tags"), f"{context}.tags", errors)
        languages = self._parse_string_set(raw.get("languages", ["any"]), f"{context}.languages", errors)

        for field_name in ("id", "name", "description", "rationale", "detection", "recommendation"):
            if not isinstance(raw.get(field_name), str) or not raw[field_name].strip():
                errors.append(f"{context}.{field_name} must be a non-empty string.")

        if errors:
            raise RuleValidationError(errors)

        return EnergyRule(
            id=raw["id"],
            name=raw["name"],
            description=raw["description"],
            category=category,
            severity=severity,
            confidence=confidence,
            rationale=raw["rationale"],
            detection=raw["detection"],
            recommendation=raw["recommendation"],
            references=references,
            version=version,
            tags=frozenset(tags),
            languages=frozenset(languages),
        )

    def _missing_field_errors(self, raw: dict[str, Any], context: str) -> list[str]:
        return [f"{context} is missing required field '{field}'." for field in sorted(self.REQUIRED_RULE_FIELDS - raw.keys())]

    def _parse_confidence(self, raw: object, context: str, errors: list[str]) -> RuleConfidence:
        if isinstance(raw, dict):
            value = raw.get("value")
            rationale = raw.get("rationale")
        else:
            value = raw
            rationale = None
        if not isinstance(value, (float, int)):
            errors.append(f"{context}.confidence.value must be numeric.")
            return RuleConfidence(0.0)
        try:
            return RuleConfidence(float(value), rationale if isinstance(rationale, str) else None)
        except ValueError as exc:
            errors.append(f"{context}.confidence.value {exc}")
            return RuleConfidence(0.0)

    def _parse_version(self, raw: object, context: str, errors: list[str]) -> RuleVersion:
        if not isinstance(raw, str):
            errors.append(f"{context}.version must be a string.")
            return RuleVersion(0, 0, 0)
        try:
            return RuleVersion.parse(raw)
        except ValueError as exc:
            errors.append(f"{context}.version {exc}")
            return RuleVersion(0, 0, 0)

    def _parse_references(self, raw: object, context: str, errors: list[str]) -> list[RuleReference]:
        if not isinstance(raw, list) or not raw:
            errors.append(f"{context}.references must be a non-empty list.")
            return []
        references: list[RuleReference] = []
        for index, item in enumerate(raw):
            if not isinstance(item, dict):
                errors.append(f"{context}.references[{index}] must be an object.")
                continue
            title = item.get("title")
            if not isinstance(title, str) or not title.strip():
                errors.append(f"{context}.references[{index}].title must be a non-empty string.")
                continue
            url = item.get("url")
            doi = item.get("doi")
            if url is not None and not isinstance(url, str):
                errors.append(f"{context}.references[{index}].url must be a string when provided.")
            if doi is not None and not isinstance(doi, str):
                errors.append(f"{context}.references[{index}].doi must be a string when provided.")
            year = item.get("year")
            if year is not None and (not isinstance(year, int) or year < 1900):
                errors.append(f"{context}.references[{index}].year must be an integer >= 1900 when provided.")
            authors = item.get("authors", [])
            if not isinstance(authors, list) or not all(isinstance(author, str) for author in authors):
                errors.append(f"{context}.references[{index}].authors must be a list of strings when provided.")
                authors = []
            references.append(RuleReference(title=title, url=url, authors=authors, year=year, doi=doi))
        return references

    def _parse_string_set(self, raw: object, context: str, errors: list[str]) -> set[str]:
        if not isinstance(raw, list) or not raw:
            errors.append(f"{context} must be a non-empty list of strings.")
            return set()
        values: set[str] = set()
        for index, value in enumerate(raw):
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{context}[{index}] must be a non-empty string.")
            else:
                values.add(value)
        return values

    def _duplicate_id_errors(self, rules: list[EnergyRule]) -> list[str]:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for rule in rules:
            if rule.id in seen:
                duplicates.add(rule.id)
            seen.add(rule.id)
        return [f"Duplicate rule id '{rule_id}'." for rule_id in sorted(duplicates)]
