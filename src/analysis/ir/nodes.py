"""Language-neutral internal representation contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol


class IRNodeKind(str, Enum):
    """Portable node categories shared by future language frontends."""

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    LOOP = "loop"
    CALL = "call"
    IMPORT = "import"
    ASSIGNMENT = "assignment"
    BRANCH = "branch"
    EXCEPTION = "exception"
    ASYNC_OPERATION = "async_operation"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class IRLocation:
    """Language-neutral source location."""

    source_file: Path
    start_line: int | None = None
    end_line: int | None = None
    start_column: int | None = None
    end_column: int | None = None


@dataclass(frozen=True)
class IRScope:
    """Portable lexical scope descriptor."""

    name: str
    parent: str | None = None
    language: str = "python"


@dataclass
class IRNode:
    """Minimal IR node for future language-independent analyses."""

    kind: IRNodeKind
    name: str | None
    location: IRLocation
    scope: IRScope
    children: list["IRNode"] = field(default_factory=list)


class IRVisitor(Protocol):
    """Protocol for future analyses that consume language-independent IR."""

    def visit(self, node: IRNode) -> None:
        """Visit one IR node."""
