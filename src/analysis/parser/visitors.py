"""Shared visitor infrastructure."""

from __future__ import annotations

import ast
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class VisitorContext:
    """Tracks lexical scope while visitors walk the tree."""

    scope_stack: list[str] = field(default_factory=lambda: ["<module>"])
    class_stack: list[str] = field(default_factory=list)
    function_stack: list[str] = field(default_factory=list)

    @property
    def scope(self) -> str:
        return ".".join(self.scope_stack[1:]) or "<module>"

    @property
    def parent_class(self) -> str | None:
        return self.class_stack[-1] if self.class_stack else None

    @property
    def parent_function(self) -> str | None:
        return self.function_stack[-1] if self.function_stack else None

    @contextmanager
    def class_scope(self, name: str) -> Iterator[None]:
        qualified = self._qualify(name)
        self.scope_stack.append(name)
        self.class_stack.append(qualified)
        try:
            yield
        finally:
            self.class_stack.pop()
            self.scope_stack.pop()

    @contextmanager
    def function_scope(self, name: str) -> Iterator[None]:
        qualified = self._qualify(name)
        self.scope_stack.append(name)
        self.function_stack.append(qualified)
        try:
            yield
        finally:
            self.function_stack.pop()
            self.scope_stack.pop()

    def _qualify(self, name: str) -> str:
        prefix = ".".join(self.scope_stack[1:])
        return f"{prefix}.{name}" if prefix else name


class ContextualVisitor(ast.NodeVisitor):
    """Base visitor that tracks function and class scope."""

    def __init__(self) -> None:
        self.context = VisitorContext()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        with self.context.class_scope(node.name):
            self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        with self.context.function_scope(node.name):
            self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        with self.context.function_scope(node.name):
            self.generic_visit(node)
