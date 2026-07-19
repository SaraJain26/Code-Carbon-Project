"""Async syntax visitor."""

from __future__ import annotations

import ast

from analysis.models import AsyncInfo
from analysis.parser.visitors import ContextualVisitor


class AsyncVisitor(ContextualVisitor):
    """Extracts async functions, await, async for, and async with usage."""

    def __init__(self) -> None:
        super().__init__()
        self.async_operations: list[AsyncInfo] = []

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        scope = self.context._qualify(node.name)
        self.async_operations.append(AsyncInfo("async_function", node.lineno, scope))
        with self.context.function_scope(node.name):
            self.generic_visit(node)

    def visit_Await(self, node: ast.Await) -> None:
        self.async_operations.append(AsyncInfo("await", node.lineno, self.context.parent_function or self.context.scope))
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.async_operations.append(AsyncInfo("async_for", node.lineno, self.context.parent_function or self.context.scope))
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self.async_operations.append(AsyncInfo("async_with", node.lineno, self.context.parent_function or self.context.scope))
        self.generic_visit(node)
