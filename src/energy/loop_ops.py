"""Static estimate of operations weighted by their enclosing loop depth."""

from __future__ import annotations

import ast


ITERATION_ESTIMATE = 10


class LoopWeightedOps(ast.NodeVisitor):
    """Count arithmetic and calls, weighting deeper loops more heavily."""

    def __init__(self, iterations: int = ITERATION_ESTIMATE) -> None:
        self.iterations = iterations
        self.depth = 0
        self.cost = 0.0

    def _visit_loop(self, node: ast.AST) -> None:
        self.depth += 1
        self.generic_visit(node)
        self.depth -= 1

    visit_For = _visit_loop
    visit_While = _visit_loop
    visit_AsyncFor = _visit_loop
    visit_ListComp = _visit_loop
    visit_SetComp = _visit_loop
    visit_DictComp = _visit_loop
    visit_GeneratorExp = _visit_loop

    def _weight(self) -> float:
        return float(self.iterations ** self.depth)

    @staticmethod
    def _has_nonconstant_operand(node: ast.BinOp) -> bool:
        constant_expression_nodes = (
            ast.Constant,
            ast.BinOp,
            ast.operator,
            ast.unaryop,
        )
        return not all(
            isinstance(child, constant_expression_nodes)
            for child in ast.walk(node)
        )

    def visit_BinOp(self, node: ast.BinOp) -> None:
        # Ignore expressions CPython can fold at compile time, such as 3 * 4.
        if self._has_nonconstant_operand(node):
            self.cost += self._weight()
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self.cost += 2.0 * self._weight()
        self.generic_visit(node)


def loop_weighted_ops(source: str) -> float:
    """Return weighted operation cost for Python source code."""
    visitor = LoopWeightedOps()
    visitor.visit(ast.parse(source))
    return visitor.cost
