"""Function extraction visitor."""

from __future__ import annotations

import ast

from analysis.models import FunctionInfo, ParameterInfo
from analysis.parser.ast_models import assigned_names, call_name, unparse
from analysis.parser.visitors import ContextualVisitor


class FunctionVisitor(ContextualVisitor):
    """Extracts Python function and async function structures."""

    def __init__(self) -> None:
        super().__init__()
        self.functions: list[FunctionInfo] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record_function(node, is_async=False)
        with self.context.function_scope(node.name):
            self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record_function(node, is_async=True)
        with self.context.function_scope(node.name):
            self.generic_visit(node)

    def _record_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool) -> None:
        qualified = self.context._qualify(node.name)
        local_variables: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = getattr(child, "targets", [getattr(child, "target", None)])
                for target in targets:
                    if target is not None:
                        local_variables.update(assigned_names(target))

        self.functions.append(
            FunctionInfo(
                name=node.name,
                qualified_name=qualified,
                line_number=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
                parameters=self._parameters(node.args),
                decorators=[unparse(decorator) or "" for decorator in node.decorator_list],
                is_async=is_async,
                is_recursive=self._has_direct_recursion(node),
                return_annotation=unparse(node.returns),
                docstring=ast.get_docstring(node),
                local_variables=local_variables,
                statement_count=len(node.body),
                line_count=getattr(node, "end_lineno", node.lineno) - node.lineno + 1,
                parent_class=self.context.parent_class,
            )
        )

    def _parameters(self, args: ast.arguments) -> list[ParameterInfo]:
        params: list[ParameterInfo] = []
        positional = list(args.posonlyargs) + list(args.args)
        defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
        for arg, default in zip(positional, defaults):
            params.append(ParameterInfo(arg.arg, unparse(arg.annotation), unparse(default)))
        if args.vararg:
            params.append(ParameterInfo(args.vararg.arg, unparse(args.vararg.annotation), kind="vararg"))
        for arg, default in zip(args.kwonlyargs, args.kw_defaults):
            params.append(ParameterInfo(arg.arg, unparse(arg.annotation), unparse(default), "keyword_only"))
        if args.kwarg:
            params.append(ParameterInfo(args.kwarg.arg, unparse(args.kwarg.annotation), kind="kwarg"))
        return params

    def _has_direct_recursion(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        return any(isinstance(child, ast.Call) and call_name(child.func).split(".")[-1] == node.name for child in ast.walk(node))
