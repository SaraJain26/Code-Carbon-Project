"""Scope-aware symbol table for Python source."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SymbolKind(str, Enum):
    """Kinds of symbols tracked by the static analyzer."""

    VARIABLE = "variable"
    FUNCTION = "function"
    CLASS = "class"
    IMPORT = "import"
    PARAMETER = "parameter"


@dataclass
class SymbolInfo:
    """One named symbol occurrence."""

    name: str
    kind: SymbolKind
    scope: str
    line_number: int
    assignments: list[int] = field(default_factory=list)
    references: list[int] = field(default_factory=list)


@dataclass
class ScopeInfo:
    """A lexical scope and its parent-child relationship."""

    name: str
    parent: str | None
    symbols: dict[str, SymbolInfo] = field(default_factory=dict)
    children: list[str] = field(default_factory=list)


class SymbolTable:
    """Mutable table of scopes and symbols."""

    def __init__(self) -> None:
        self.scopes: dict[str, ScopeInfo] = {"<module>": ScopeInfo("<module>", None)}

    def add_scope(self, name: str, parent: str | None) -> None:
        if name not in self.scopes:
            self.scopes[name] = ScopeInfo(name=name, parent=parent)
        if parent and name not in self.scopes[parent].children:
            self.scopes[parent].children.append(name)

    def define(self, name: str, kind: SymbolKind, scope: str, line_number: int) -> None:
        self.add_scope(scope, self.scopes.get(scope, ScopeInfo(scope, None)).parent)
        symbols = self.scopes[scope].symbols
        if name not in symbols:
            symbols[name] = SymbolInfo(name=name, kind=kind, scope=scope, line_number=line_number)

    def assign(self, name: str, scope: str, line_number: int) -> None:
        self.define(name, SymbolKind.VARIABLE, scope, line_number)
        self.scopes[scope].symbols[name].assignments.append(line_number)

    def reference(self, name: str, scope: str, line_number: int) -> None:
        target_scope = self.resolve_scope(name, scope) or scope
        self.define(name, SymbolKind.VARIABLE, target_scope, line_number)
        self.scopes[target_scope].symbols[name].references.append(line_number)

    def resolve_scope(self, name: str, scope: str) -> str | None:
        current = self.scopes.get(scope)
        while current is not None:
            if name in current.symbols:
                return current.name
            current = self.scopes.get(current.parent or "")
        return None
