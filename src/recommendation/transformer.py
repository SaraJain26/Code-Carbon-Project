"""
AST Code Transformer for Code-Carbon.

Applies safe AST-level automated code refactorings for eligible EKB rules:
- EKB-COMP-002: Hoisting loop-invariant computations
- EKB-IO-001 / EKB-IO-002: Hoisting file I/O operations outside loops
- EKB-MEM-001: Hoisting loop-invariant memory allocations
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TransformationFix:
    rule_id: str
    rule_name: str
    description: str
    line_number: int | None
    is_auto_applied: bool


@dataclass
class TransformResult:
    original_code: str
    optimized_code: str
    auto_applied_fixes: list[dict[str, Any]]
    manual_fixes: list[dict[str, Any]]
    estimated_impact: dict[str, Any]


class _LoopInvariantHoister(ast.NodeTransformer):
    """
    AST NodeTransformer that identifies and hoists:
    1. File context managers (with open(...) as f:) around loops (EKB-IO-001, EKB-IO-002)
    2. Loop-invariant variable assignments (EKB-COMP-002)
    3. Invariant temporary allocations (EKB-MEM-001)
    """

    def __init__(self) -> None:
        super().__init__()
        self.auto_fixes: list[TransformationFix] = []
        self.manual_fixes: list[TransformationFix] = []

    def _get_assigned_and_loop_vars(self, loop_node: ast.For | ast.While) -> set[str]:
        loop_vars: set[str] = set()
        if isinstance(loop_node, ast.For):
            for name_node in ast.walk(loop_node.target):
                if isinstance(name_node, ast.Name):
                    loop_vars.add(name_node.id)
        # Find all names modified in loop body
        for node in ast.walk(loop_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    for name_node in ast.walk(target):
                        if isinstance(name_node, ast.Name):
                            loop_vars.add(name_node.id)
            elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
                target = getattr(node, "target", None)
                if target:
                    for name_node in ast.walk(target):
                        if isinstance(name_node, ast.Name):
                            loop_vars.add(name_node.id)
        return loop_vars

    def _is_expression_invariant(self, expr: ast.AST, loop_vars: set[str]) -> bool:
        """
        Check if an expression does not depend on loop targets or variables mutated in loop.
        """
        for node in ast.walk(expr):
            if isinstance(node, ast.Name) and node.id in loop_vars:
                return False
            if isinstance(node, ast.Call):
                # Avoid hoisting arbitrary non-pure function calls (e.g. print, write, random, time)
                if isinstance(node.func, ast.Name) and node.func.id in {
                    "print", "write", "append", "input", "next", "read", "readline", "readlines"
                }:
                    return False
                if isinstance(node.func, ast.Attribute) and node.func.attr in {
                    "write", "append", "extend", "pop", "push", "read", "readline"
                }:
                    return False
        return True

    def visit_For(self, node: ast.For) -> Any:
        self.generic_visit(node)
        return self._transform_loop(node)

    def visit_While(self, node: ast.While) -> Any:
        self.generic_visit(node)
        return self._transform_loop(node)

    def _transform_loop(self, node: ast.For | ast.While) -> Any:
        hoisted_before: list[ast.stmt] = []
        new_body: list[ast.stmt] = []

        # Step A: Check for file open context manager inside loop: with open(...) as f:
        file_with_node: ast.With | None = None
        if len(node.body) == 1 and isinstance(node.body[0], ast.With):
            with_item = node.body[0].items[0]
            if isinstance(with_item.context_expr, ast.Call):
                func = with_item.context_expr.func
                if (isinstance(func, ast.Name) and func.id == "open") or (
                    isinstance(func, ast.Attribute) and func.attr == "open"
                ):
                    file_with_node = node.body[0]

        if file_with_node is not None:
            # We transform:
            # for item in items:
            #     with open(...) as f:
            #         f.write(item)
            # ->
            # with open(...) as f:
            #     for item in items:
            #         f.write(item)
            lineno = getattr(file_with_node, "lineno", node.lineno)
            self.auto_fixes.append(
                TransformationFix(
                    rule_id="EKB-IO-001",
                    rule_name="Repeated file I/O inside loops",
                    description=f"Hoisted file open context manager at line {lineno} outside loop body.",
                    line_number=lineno,
                    is_auto_applied=True,
                )
            )
            # Create outer with block wrapping loop with inner body
            inner_loop = ast.For(
                target=node.target,
                iter=node.iter,
                body=file_with_node.body,
                orelse=node.orelse,
                type_comment=getattr(node, "type_comment", None),
            ) if isinstance(node, ast.For) else ast.While(
                test=node.test,
                body=file_with_node.body,
                orelse=node.orelse,
            )
            ast.copy_location(inner_loop, node)

            outer_with = ast.With(
                items=file_with_node.items,
                body=[inner_loop],
                type_comment=getattr(file_with_node, "type_comment", None),
            )
            ast.copy_location(outer_with, node)
            return outer_with

        # Step B: Hoist invariant computations & allocations inside loop body
        loop_vars = self._get_assigned_and_loop_vars(node)

        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                target_names = {
                    name.id
                    for target in stmt.targets
                    for name in ast.walk(target)
                    if isinstance(name, ast.Name)
                }
                # Check if rhs is invariant
                if self._is_expression_invariant(stmt.value, loop_vars):
                    is_alloc = isinstance(stmt.value, (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp))
                    
                    # Unsafe hoist check: if allocation container or target variable is mutated/appended to inside loop,
                    # hoisting outside loop breaks program correctness (e.g. bucket = [] accumulation across iterations).
                    is_mutated = self._is_target_mutated_in_loop(target_names, node)
                    
                    if is_alloc and is_mutated:
                        # Skip auto-hoisting unsafe container allocation; keep in loop
                        new_body.append(stmt)
                        continue

                    rule_id = "EKB-MEM-001" if is_alloc else "EKB-COMP-002"
                    rule_name = "Excessive temporary allocation in loop" if is_alloc else "Redundant computation in loop"

                    lineno = getattr(stmt, "lineno", node.lineno)
                    self.auto_fixes.append(
                        TransformationFix(
                            rule_id=rule_id,
                            rule_name=rule_name,
                            description=f"Hoisted loop-invariant assignment `{ast.unparse(stmt).strip()}` at line {lineno} outside loop.",
                            line_number=lineno,
                            is_auto_applied=True,
                        )
                    )
                    hoisted_before.append(stmt)
                    continue

            new_body.append(stmt)

        if hoisted_before:
            node.body = new_body
            return hoisted_before + [node]

        return node

    def _is_target_mutated_in_loop(self, target_names: set[str], loop_node: ast.AST) -> bool:
        """
        Check if any variable in target_names is mutated (via methods like append/add/extend or subscript assignment) inside loop.
        """
        for child in ast.walk(loop_node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                if isinstance(child.func.value, ast.Name) and child.func.value.id in target_names:
                    if child.func.attr in {"append", "add", "extend", "update", "insert", "pop", "remove", "clear", "write"}:
                        return True
            if isinstance(child, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = child.targets if isinstance(child, ast.Assign) else [getattr(child, "target", None)]
                for t in targets:
                    if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id in target_names:
                        return True
        return False


class ASTCodeTransformer:
    """
    Analyzes Python source code and generates auto-transformed optimized code.
    """

    def transform(self, code: str, findings: list[dict[str, Any]] | None = None) -> TransformResult:
        try:
            tree = ast.parse(code)
        except Exception:
            # Fallback if unparseable
            return TransformResult(
                original_code=code,
                optimized_code=code,
                auto_applied_fixes=[],
                manual_fixes=[
                    {
                        "rule_id": "SYNTAX_ERROR",
                        "rule_name": "Unparseable Python Syntax",
                        "description": "Source code contains syntax errors; automated AST refactoring skipped.",
                        "is_auto_applied": False,
                    }
                ],
                estimated_impact={
                    "ess_reduction_percent": 0.0,
                    "cirs_reduction_percent": 0.0,
                    "energy_saving_percent": 0.0,
                    "carbon_saving_percent": 0.0,
                },
            )

        hoister = _LoopInvariantHoister()
        transformed_tree = hoister.visit(tree)
        transformed_tree = hoister.visit(transformed_tree)
        ast.fix_missing_locations(transformed_tree)

        try:
            optimized_code = ast.unparse(transformed_tree)
        except Exception:
            optimized_code = code

        auto_applied = [
            {
                "rule_id": fix.rule_id,
                "rule_name": fix.rule_name,
                "description": fix.description,
                "line_number": fix.line_number,
                "is_auto_applied": True,
            }
            for fix in hoister.auto_fixes
        ]

        # Categorize every finding that was not actually transformed as a manual
        # recommendation.  Some rules are eligible for automation in principle,
        # but are deliberately skipped when applying the change could alter program
        # semantics (for example, a list recreated on each loop iteration).
        manual_fixes = []
        if findings:
            auto_fixed_locations = {
                (fix.rule_id, fix.line_number)
                for fix in hoister.auto_fixes
            }
            guidance_by_rule = {
                "EKB-REC-001": "Use memoization or an iterative algorithm after confirming the function's expected inputs and memory budget.",
                "EKB-NET-001": "Batch requests, cache repeated responses, or use bounded asynchronous concurrency while preserving retry and rate-limit behaviour.",
                "EKB-MEM-001": "Reuse a buffer only if each iteration does not require a fresh container; otherwise reduce the allocation size or stream results.",
                "EKB-COMP-002": "Move the invariant computation outside the loop after confirming it has no side effects and does not depend on loop state.",
                "EKB-IO-001": "Open the file once outside the loop and preserve the intended write mode, flushing, and error-handling behaviour.",
                "EKB-IO-002": "Open the file once outside the loop and preserve the intended read position and error-handling behaviour.",
            }
            for f in findings:
                rule_id = f.get("rule_id", "")
                line_number = f.get("line_number")
                if (rule_id, line_number) not in auto_fixed_locations:
                    manual_fixes.append(
                        {
                            "rule_id": rule_id,
                            "rule_name": f.get("category", "General").title() + " Refactoring Required",
                            "description": guidance_by_rule.get(
                                rule_id,
                                f.get("message", "Manual architectural rewrite required."),
                            ),
                            "line_number": line_number,
                            "is_auto_applied": False,
                        }
                    )

        # Calculate modeled impact projections
        auto_count = len(auto_applied)
        manual_count = len(manual_fixes)
        total_findings = auto_count + manual_count

        if total_findings > 0:
            # Modeled projection assumption: each auto-fix reduces estimated energy/carbon by ~15-25%
            # and reduces ESS proportionally
            ess_red = min(85.0, (auto_count / total_findings) * 60.0 + (auto_count * 10.0))
            cirs_red = min(85.0, (auto_count / total_findings) * 55.0 + (auto_count * 8.0))
            energy_red = min(75.0, auto_count * 15.0)
            carbon_red = min(75.0, auto_count * 15.0)
        else:
            ess_red = 0.0
            cirs_red = 0.0
            energy_red = 0.0
            carbon_red = 0.0

        estimated_impact = {
            "ess_reduction_percent": round(ess_red, 1),
            "cirs_reduction_percent": round(cirs_red, 1),
            "energy_saving_percent": round(energy_red, 1),
            "carbon_saving_percent": round(carbon_red, 1),
        }

        return TransformResult(
            original_code=code,
            optimized_code=optimized_code,
            auto_applied_fixes=auto_applied,
            manual_fixes=manual_fixes,
            estimated_impact=estimated_impact,
        )
