"""Exception syntax visitor."""

from __future__ import annotations

import ast

from analysis.models import ExceptionInfo
from analysis.parser.ast_models import unparse
from analysis.parser.visitors import ContextualVisitor


class ExceptionVisitor(ContextualVisitor):
    """Extracts try/except/finally/raise and custom exception classes."""

    def __init__(self) -> None:
        super().__init__()
        self.exceptions: list[ExceptionInfo] = []

    def visit_Try(self, node: ast.Try) -> None:
        scope = self.context.parent_function or self.context.scope
        self.exceptions.append(ExceptionInfo("try", node.lineno, scope))
        for handler in node.handlers:
            self.exceptions.append(ExceptionInfo("except", handler.lineno, scope, unparse(handler.type)))
        if node.finalbody:
            self.exceptions.append(ExceptionInfo("finally", node.finalbody[0].lineno, scope))
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        self.exceptions.append(ExceptionInfo("raise", node.lineno, self.context.parent_function or self.context.scope, unparse(node.exc)))
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = {unparse(base) for base in node.bases}
        if bases & {"Exception", "BaseException"}:
            self.exceptions.append(ExceptionInfo("custom_exception", node.lineno, self.context.scope, node.name))
        with self.context.class_scope(node.name):
            self.generic_visit(node)
