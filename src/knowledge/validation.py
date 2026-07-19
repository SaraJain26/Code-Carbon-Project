"""Validation errors and helpers for EKB rules."""

from __future__ import annotations


class RuleValidationError(ValueError):
    """Raised when one or more energy rule definitions are invalid."""

    def __init__(self, messages: list[str]) -> None:
        self.messages = messages
        super().__init__("\n".join(messages))


def require_mapping(value: object, context: str) -> dict:
    """Validate that a decoded YAML value is a mapping."""

    if not isinstance(value, dict):
        raise RuleValidationError([f"{context} must be a mapping/object."])
    return value


def require_list(value: object, context: str) -> list:
    """Validate that a decoded YAML value is a list."""

    if not isinstance(value, list):
        raise RuleValidationError([f"{context} must be a list."])
    return value
