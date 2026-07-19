"""Loop extraction visitor."""

from __future__ import annotations

import ast

from analysis.models import LoopInfo, LoopType
from analysis.parser.visitors import ContextualVisitor
from analysis.utils import CallClassifier, CallInspection, is_async_operation


class LoopVisitor(ContextualVisitor):
    """Extracts loops and loop-local structural signals."""

    def __init__(self) -> None:
        super().__init__()
        self.loops: list[LoopInfo] = []
        self.classifier = CallClassifier()
        self._loop_depth = 0

    def visit_For(self, node: ast.For) -> None:
        self._record_loop(node, LoopType.FOR)

    def visit_While(self, node: ast.While) -> None:
        self._record_loop(node, LoopType.WHILE)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._record_loop(node, LoopType.ASYNC_FOR)

    def _record_loop(self, node: ast.For | ast.While | ast.AsyncFor, loop_type: LoopType) -> None:
        self._loop_depth += 1
        self.loops.append(
            LoopInfo(
                loop_type=loop_type,
                line_number=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
                nesting_depth=self._loop_depth,
                parent_function=self.context.parent_function,
                parent_class=self.context.parent_class,
                contains_api_call=self._contains_api_call(node),
                contains_file_io=self._contains_file_io(node),
                contains_recursion=self._contains_recursion(node),
                contains_async_operations=loop_type is LoopType.ASYNC_FOR or is_async_operation(node),
            )
        )
        self.generic_visit(node)
        self._loop_depth -= 1

    def _contains_api_call(self, node: ast.AST) -> bool:
        return any(
            isinstance(child, ast.Call) and self.classifier.is_network_operation(CallInspection.from_call(child))
            for child in ast.walk(node)
        )

    def _contains_file_io(self, node: ast.AST) -> bool:
        return any(
            isinstance(child, ast.Call) and self.classifier.is_file_operation(CallInspection.from_call(child))
            for child in ast.walk(node)
        )

    def _contains_recursion(self, node: ast.AST) -> bool:
        function_name = (self.context.parent_function or "").split(".")[-1]
        return bool(function_name) and any(
            isinstance(child, ast.Call) and CallInspection.from_call(child).leaf_name == function_name
            for child in ast.walk(node)
        )
