"""Symbol table construction visitor."""

from __future__ import annotations

import ast

from analysis.parser.ast_models import assigned_names
from analysis.parser.visitors import ContextualVisitor
from analysis.symbols import SymbolKind, SymbolTable


class SymbolVisitor(ContextualVisitor):
    """Builds a scope-aware symbol table."""

    def __init__(self) -> None:
        super().__init__()
        self.symbol_table = SymbolTable()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.symbol_table.define(alias.asname or alias.name.split(".")[0], SymbolKind.IMPORT, self.context.scope, node.lineno)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            self.symbol_table.define(alias.asname or alias.name, SymbolKind.IMPORT, self.context.scope, node.lineno)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.symbol_table.define(node.name, SymbolKind.CLASS, self.context.scope, node.lineno)
        qualified = self.context._qualify(node.name)
        self.symbol_table.add_scope(qualified, self.context.scope)
        with self.context.class_scope(node.name):
            self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            for name in assigned_names(target):
                self.symbol_table.assign(name, self.context.scope, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        for name in assigned_names(node.target):
            self.symbol_table.assign(name, self.context.scope, node.lineno)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        for name in assigned_names(node.target):
            self.symbol_table.assign(name, self.context.scope, node.lineno)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.symbol_table.reference(node.id, self.context.scope, node.lineno)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.symbol_table.define(node.name, SymbolKind.FUNCTION, self.context.scope, node.lineno)
        qualified = self.context._qualify(node.name)
        self.symbol_table.add_scope(qualified, self.context.scope)
        with self.context.function_scope(node.name):
            for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
                self.symbol_table.define(arg.arg, SymbolKind.PARAMETER, self.context.scope, node.lineno)
            if node.args.vararg:
                self.symbol_table.define(node.args.vararg.arg, SymbolKind.PARAMETER, self.context.scope, node.lineno)
            if node.args.kwarg:
                self.symbol_table.define(node.args.kwarg.arg, SymbolKind.PARAMETER, self.context.scope, node.lineno)
            self.generic_visit(node)
