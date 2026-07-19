"""Lightweight control-flow graph visitor."""

from __future__ import annotations

import ast

from analysis.cfg import ControlFlowGraph
from analysis.parser.visitors import ContextualVisitor


class CFGVisitor(ContextualVisitor):
    """Builds a pragmatic CFG over functions and modules."""

    CONTROL_NODES = (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Break,
        ast.Continue,
        ast.Return,
        ast.Try,
        ast.Raise,
        ast.ExceptHandler,
    )

    def __init__(self) -> None:
        super().__init__()
        self.graph = ControlFlowGraph()
        self._last_by_scope: dict[str, int] = {}

    def visit_Module(self, node: ast.Module) -> None:
        entry = self.graph.add_node("module_entry", "Module", None, "<module>")
        self._last_by_scope["<module>"] = entry
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node, "FunctionDef")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node, "AsyncFunctionDef")

    def visit_If(self, node: ast.If) -> None:
        current = self._add_control(node, "if", "If")
        previous = self._last_by_scope.get(self.context.scope)
        if previous and previous != current:
            self.graph.add_edge(previous, current, "condition")
        self._last_by_scope[self.context.scope] = current
        for child in node.body:
            self.visit(child)
        for child in node.orelse:
            self.graph.add_edge(current, self.graph.add_node("else", "Else", getattr(child, "lineno", None), self.context.scope), "else")
            self.visit(child)

    def visit_For(self, node: ast.For) -> None:
        self._visit_loop(node, "for")

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._visit_loop(node, "async_for")

    def visit_While(self, node: ast.While) -> None:
        self._visit_loop(node, "while")

    def generic_visit(self, node: ast.AST) -> None:
        if isinstance(node, self.CONTROL_NODES) and not isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While)):
            self._add_control(node, node.__class__.__name__.lower(), node.__class__.__name__)
        super().generic_visit(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, node_type: str) -> None:
        function_scope = self.context._qualify(node.name)
        entry = self.graph.add_node(f"{function_scope}_entry", node_type, node.lineno, function_scope)
        self._last_by_scope[function_scope] = entry
        with self.context.function_scope(node.name):
            for child in node.body:
                self.visit(child)

    def _visit_loop(self, node: ast.For | ast.AsyncFor | ast.While, label: str) -> None:
        loop_id = self._add_control(node, label, node.__class__.__name__)
        for child in node.body:
            self.visit(child)
        self.graph.add_edge(self._last_by_scope.get(self.context.scope, loop_id), loop_id, "loop")

    def _add_control(self, node: ast.AST, label: str, node_type: str) -> int:
        scope = self.context.scope
        node_id = self.graph.add_node(label, node_type, getattr(node, "lineno", None), scope)
        previous = self._last_by_scope.get(scope)
        if previous and previous != node_id:
            self.graph.add_edge(previous, node_id)
        self._last_by_scope[scope] = node_id
        return node_id
