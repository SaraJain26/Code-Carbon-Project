"""Class extraction visitor."""

from __future__ import annotations

import ast

from analysis.models import ClassInfo
from analysis.parser.ast_models import assigned_names, unparse
from analysis.parser.visitors import ContextualVisitor


class ClassVisitor(ContextualVisitor):
    """Extracts class declarations, inheritance, methods, and class variables."""

    def __init__(self) -> None:
        super().__init__()
        self.classes: list[ClassInfo] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qualified = self.context._qualify(node.name)
        methods = [item.name for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))]
        class_variables: set[str] = set()
        for item in node.body:
            if isinstance(item, (ast.Assign, ast.AnnAssign)):
                targets = getattr(item, "targets", [getattr(item, "target", None)])
                for target in targets:
                    if target is not None:
                        class_variables.update(assigned_names(target))
        self.classes.append(
            ClassInfo(
                name=node.name,
                qualified_name=qualified,
                line_number=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
                bases=[unparse(base) or "" for base in node.bases],
                decorators=[unparse(decorator) or "" for decorator in node.decorator_list],
                methods=methods,
                class_variables=class_variables,
                docstring=ast.get_docstring(node),
            )
        )
        with self.context.class_scope(node.name):
            self.generic_visit(node)
