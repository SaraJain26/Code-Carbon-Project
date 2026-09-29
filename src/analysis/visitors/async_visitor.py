"""Async syntax visitor."""

from __future__ import annotations

import ast

from analysis.models import AsyncInfo
from analysis.parser.ast_models import call_name
from analysis.parser.visitors import ContextualVisitor


class AsyncVisitor(ContextualVisitor):
    """Extracts async syntax metadata and blocking synchronous operations inside async function workflows."""

    def __init__(self) -> None:
        super().__init__()
        self.async_operations: list[AsyncInfo] = []
        self._async_func_depth = 0

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        scope = self.context._qualify(node.name)
        self.async_operations.append(AsyncInfo("async_function", node.lineno, scope))
        self._async_func_depth += 1
        with self.context.function_scope(node.name):
            self.generic_visit(node)
        self._async_func_depth -= 1

    def visit_Await(self, node: ast.Await) -> None:
        scope = self.context.parent_function or self.context.scope
        self.async_operations.append(AsyncInfo("await", node.lineno, scope))
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        scope = self.context.parent_function or self.context.scope
        self.async_operations.append(AsyncInfo("async_for", node.lineno, scope))
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        scope = self.context.parent_function or self.context.scope
        self.async_operations.append(AsyncInfo("async_with", node.lineno, scope))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if self._async_func_depth > 0:
            name = call_name(node.func)
            if self._is_blocking_call(node, name):
                scope = self.context.parent_function or self.context.scope
                self.async_operations.append(
                    AsyncInfo(
                        operation=f"blocking:{name}",
                        line_number=node.lineno,
                        scope=scope,
                    )
                )
        self.generic_visit(node)

    def _is_blocking_call(self, node: ast.Call, name: str) -> bool:
        # 1. Synchronous time.sleep in async function
        if name in ("time.sleep", "sleep"):
            return True

        # 2. Synchronous network requests in async function
        if name.startswith(("requests.", "urllib.request.", "http.client.", "socket.")):
            return True

        # 3. Synchronous built-in file open in async function
        if name == "open" or name.startswith(("os.open", "io.open")):
            return True

        # 4. Synchronous subprocess execution in async function
        if name.startswith(("subprocess.", "os.system", "os.popen")):
            return True

        return False
