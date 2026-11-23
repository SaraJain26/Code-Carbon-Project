"""
AST Code Transformer for Code-Carbon.

Applies safe AST-level automated code refactorings for eligible EKB rules:
- EKB-COMP-002: Hoisting loop-invariant computations
- EKB-IO-001 / EKB-IO-002: Hoisting file I/O operations outside loops
- EKB-MEM-001: Hoisting loop-invariant memory allocations
"""

from __future__ import annotations

import ast
import copy
import difflib
import hashlib
import io
import re
import tokenize
import textwrap
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable

from knowledge.loader import RuleLoader


@dataclass
class TransformationFix:
    rule_id: str
    rule_name: str
    description: str
    line_number: int | None
    is_auto_applied: bool
    line_start: int | None = None
    line_end: int | None = None
    original_code: str | None = None
    replacement_code: str | None = None


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
    PURE_BUILTINS = {"abs", "all", "any", "bool", "float", "int", "len", "max", "min", "sum", "tuple"}

    @classmethod
    def _safe_builtin_call(cls, call: ast.Call) -> bool:
        """Only hoist calls whose literal arguments are known not to raise."""
        if not isinstance(call.func, ast.Name) or call.func.id not in cls.PURE_BUILTINS:
            return False
        if call.func.id == "sum" and len(call.args) == 1 and isinstance(call.args[0], ast.Tuple):
            return all(isinstance(v, ast.Constant) and isinstance(v.value, (int, float, complex, bool)) for v in call.args[0].elts)
        if call.func.id == "len" and len(call.args) == 1 and isinstance(call.args[0], (ast.Tuple, ast.List, ast.Constant)):
            return True
        if call.func.id == "abs" and len(call.args) == 1 and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, (int, float, complex, bool)):
            return True
        if call.func.id in {"min", "max"} and len(call.args) == 1 and isinstance(call.args[0], (ast.Tuple, ast.List)):
            values = call.args[0].elts
            return bool(values) and all(isinstance(v, ast.Constant) and isinstance(v.value, (int, float)) for v in values)
        return False

    def __init__(self, source_code: str = "") -> None:
        super().__init__()
        self.auto_fixes: list[TransformationFix] = []
        self.manual_fixes: list[TransformationFix] = []
        self.source_lines = source_code.splitlines(keepends=True)

    def _source_fragment(self, node: ast.AST) -> tuple[int | None, int | None, str]:
        line_start = getattr(node, "lineno", None)
        line_end = getattr(node, "end_lineno", line_start)
        if not isinstance(line_start, int) or not isinstance(line_end, int):
            return None, None, ""
        fragment = "".join(self.source_lines[line_start - 1:line_end]).rstrip("\r\n")
        return line_start, line_end, fragment

    def _replacement_fragment(self, node: ast.AST, line_start: int | None) -> str:
        rendered = ast.unparse(node)
        if not isinstance(line_start, int) or not 0 < line_start <= len(self.source_lines):
            return rendered
        original_line = self.source_lines[line_start - 1].rstrip("\r\n")
        indent = original_line[:len(original_line) - len(original_line.lstrip())]
        return textwrap.indent(rendered, indent) if indent else rendered

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
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"append", "extend", "insert", "pop", "remove", "clear", "update", "add", "discard"}
                and isinstance(node.func.value, ast.Name)
            ):
                # Mark the receiver as mutable so e.g. len(values) is not
                # hoisted above a loop that appends to values.
                loop_vars.add(node.func.value.id)
        return loop_vars

    def _is_expression_invariant(self, expr: ast.AST, loop_vars: set[str]) -> bool:
        """
        Check if an expression does not depend on loop targets or variables mutated in loop.
        """
        for node in ast.walk(expr):
            if isinstance(node, ast.Name) and node.id in loop_vars:
                return False
            # Calls, attribute reads, and subscripts may have side effects or
            # return different values between iterations. Keep them in place.
            if isinstance(node, ast.Call):
                if not self._safe_builtin_call(node):
                    return False
            if isinstance(node, (ast.Attribute, ast.Subscript)):
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
        loop_fix_start = len(self.auto_fixes)
        line_start, line_end, original_code = self._source_fragment(node)

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
            open_call = file_with_node.items[0].context_expr
            path = open_call.args[0] if open_call.args else None
            mode = open_call.args[1] if len(open_call.args) == 2 else None
            append_modes = {"a", "ab", "at", "a+", "ab+", "at+"}
            safe_open = (
                isinstance(open_call.func, ast.Name)
                and open_call.func.id == "open"
                and not open_call.keywords
                and isinstance(path, ast.Constant)
                and isinstance(path.value, str)
                and isinstance(mode, ast.Constant)
                and mode.value in append_modes
            )
            if not safe_open:
                # Moving read, truncate, or default-mode opens changes file
                # position, path evaluation, or truncation behavior across iterations.
                file_with_node = None

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
            line_start, line_end, original_code = self._source_fragment(node)
            self.auto_fixes.append(
                TransformationFix(
                    rule_id="EKB-IO-001",
                    rule_name="Repeated file I/O inside loops",
                    description=f"Hoisted file open context manager at line {lineno} outside loop body.",
                    line_number=lineno,
                    is_auto_applied=True,
                    line_start=line_start,
                    line_end=line_end,
                    original_code=original_code,
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
            self.auto_fixes[-1].replacement_code = self._replacement_fragment(outer_with, line_start)
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
                            line_start=line_start,
                            line_end=line_end,
                            original_code=original_code,
                        )
                    )
                    hoisted_before.append(stmt)
                    continue

            new_body.append(stmt)

        if hoisted_before:
            node.body = new_body
            replacement_module = ast.Module(body=hoisted_before + [node], type_ignores=[])
            replacement_code = self._replacement_fragment(replacement_module, line_start)
            for fix in self.auto_fixes[loop_fix_start:]:
                fix.replacement_code = replacement_code
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
                estimated_impact={},
            )

        hoister = _LoopInvariantHoister(code)
        transformed_tree = hoister.visit(tree)
        transformed_tree = hoister.visit(transformed_tree)
        ast.fix_missing_locations(transformed_tree)

        if not hoister.auto_fixes:
            optimized_code = code
        else:
            try:
                optimized_code = ast.unparse(transformed_tree)
            except Exception:
                optimized_code = code

        verified_fixes = hoister.auto_fixes if optimized_code != code else []
        auto_applied = [
            {
                "rule_id": fix.rule_id,
                "rule_name": fix.rule_name,
                "description": fix.description,
                "line_number": fix.line_number,
                "line_start": fix.line_start,
                "line_end": fix.line_end,
                "original_code": fix.original_code,
                "replacement_code": fix.replacement_code,
                "is_auto_applied": True,
            }
            for fix in verified_fixes
        ]

        # Categorize every finding that was not actually transformed as a manual
        # recommendation.  Some rules are eligible for automation in principle,
        # but are deliberately skipped when applying the change could alter program
        # semantics (for example, a list recreated on each loop iteration).
        manual_fixes = []
        if findings:
            auto_fixed_locations = {
                (fix.rule_id, fix.line_number)
                for fix in verified_fixes
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
                            "line_start": line_number,
                            "line_end": f.get("end_line") or line_number,
                            "original_code": "".join(code.splitlines(keepends=True)[line_number - 1:(f.get("end_line") or line_number)]).rstrip("\r\n") if isinstance(line_number, int) and line_number > 0 else None,
                            "replacement_code": None,
                            "unavailable_reason": "No verified automatic transformation exists for this finding. Review the recommendation and make the change manually.",
                            "is_auto_applied": False,
                        }
                    )

        # Impact is recalculated by the analysis pipeline; avoid fixed savings
        # percentages that can contradict those model outputs.
        estimated_impact: dict[str, Any] = {}

        return TransformResult(
            original_code=code,
            optimized_code=optimized_code,
            auto_applied_fixes=auto_applied,
            manual_fixes=manual_fixes,
            estimated_impact=estimated_impact,
        )


# A separate, source-preserving recommendation pipeline. It intentionally
# coexists with ASTCodeTransformer: that class still owns the legacy hoister
# and its output contract.
TransformerFunction = Callable[[str, Any], dict[str, str] | None]
TRANSFORMER_REGISTRY: dict[str, TransformerFunction] = {}
registry = TRANSFORMER_REGISTRY


def transformer(rule_id: str) -> Callable[[TransformerFunction], TransformerFunction]:
    """Register a narrow source rewrite for one finding rule."""
    def register(function: TransformerFunction) -> TransformerFunction:
        TRANSFORMER_REGISTRY[rule_id] = function
        return function
    return register


_RECOMMENDATION_PIPELINE = None
_RECOMMENDATION_CACHE: dict[tuple[str, str, int | None], dict[str, str] | None] = {}


def analyze(source: str) -> Counter[str]:
    """Run the repository's real static analyzer and count findings per rule."""
    global _RECOMMENDATION_PIPELINE
    from pipeline import PredictivePipeline

    if _RECOMMENDATION_PIPELINE is None:
        _RECOMMENDATION_PIPELINE = PredictivePipeline()
    pipeline = _RECOMMENDATION_PIPELINE
    result = pipeline._analysis_engine.analyze_source(source, "<recommendation>")
    report = pipeline._detect(result)
    return Counter(finding.rule_id for finding in report.findings)


def passes_gate(
    source: str,
    new_source: str,
    *,
    analyze_fn: Callable[[str], Any] | None = None,
) -> bool:
    """Check syntax, actual change, undefined-name delta, and finding regressions."""
    if not isinstance(new_source, str) or new_source == source:
        return False
    try:
        original_tree = ast.parse(source)
        candidate_tree = ast.parse(new_source)
        compile(original_tree, "<recommendation-original>", "exec")
        compile(candidate_tree, "<recommendation-candidate>", "exec")
    except (SyntaxError, TypeError, ValueError):
        return False
    if ast.dump(original_tree, include_attributes=False) == ast.dump(candidate_tree, include_attributes=False):
        return False

    if not _undefined_name_set(new_source).issubset(_undefined_name_set(source)):
        return False

    analyzer = analyze_fn or analyze
    try:
        before = _finding_counter(analyzer(source))
        after = _finding_counter(analyzer(new_source))
    except Exception:
        return False
    return all(after[rule] <= before[rule] for rule in after)


def _finding_counter(findings: Any) -> Counter[str]:
    if isinstance(findings, Counter):
        return Counter(findings)
    if isinstance(findings, dict):
        return Counter(findings)
    counts: Counter[str] = Counter()
    for finding in findings or ():
        rule_id = finding.get("rule_id") if isinstance(finding, dict) else getattr(finding, "rule_id", None)
        if rule_id:
            counts[str(rule_id)] += 1
    return counts


def _undefined_name_set(source: str) -> set[str]:
    try:
        import ast as _ast
        from pyflakes.checker import Checker
        from pyflakes.messages import UndefinedName

        checker = Checker(_ast.parse(source), filename="<recommendation>")
        return {str(message.message_args[0]) for message in checker.messages if isinstance(message, UndefinedName)}
    except ImportError:
        # pyflakes is declared in requirements.txt; retain the local
        # symtable-compatible fallback for source checkouts before install.
        from recommendation.location_suggestions import _undefined_names
        return _undefined_names(source)
    except SyntaxError:
        return {"<syntax>"}


def _target_names(target: ast.AST) -> set[str]:
    return {node.id for node in ast.walk(target) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)}


def _scope_unit(tree: ast.Module, target: ast.AST) -> ast.AST:
    parents: dict[int, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent
    scopes: list[ast.AST] = []
    current = target
    while id(current) in parents:
        current = parents[id(current)]
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            scopes.append(current)
    return scopes[0] if scopes else tree


def used_outside(unit: ast.AST, loop: ast.AST, names: set[str]) -> bool:
    """Refuse loop-variable bindings observable outside the loop, in any order."""
    inside_ids = {id(node) for node in ast.walk(loop)}
    outside = [node for node in ast.walk(unit) if id(node) not in inside_ids]
    if any(isinstance(node, ast.Name) and node.id in names and isinstance(node.ctx, ast.Load) for node in outside):
        return True

    stores: dict[str, list[tuple[int, int]]] = {name: [] for name in names}
    loads: dict[str, list[tuple[int, int]]] = {name: [] for name in names}
    for node in outside:
        if isinstance(node, ast.Name) and node.id in names:
            position = (getattr(node, "lineno", 0), getattr(node, "col_offset", 0))
            if isinstance(node.ctx, ast.Store):
                stores[node.id].append(position)
            elif isinstance(node.ctx, ast.Load):
                loads[node.id].append(position)
    return any(store < load for name in names for store in stores[name] for load in loads[name])


def _contains_comment(source: str, first_line: int, last_line: int) -> bool:
    try:
        return any(
            token.type == tokenize.COMMENT and first_line <= token.start[0] <= last_line
            for token in tokenize.generate_tokens(io.StringIO(source).readline)
        )
    except (tokenize.TokenError, IndentationError):
        return True


def _pure_join_expression(node: ast.AST, target_names: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in target_names
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _pure_join_expression(node.left, target_names) and _pure_join_expression(node.right, target_names)
    return False


@transformer("EKB-MEM-001")
def concat_to_join(source: str, finding: Any = None) -> dict[str, str] | None:
    """Rewrite a simple repeated string concatenation with a source-only splice."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, TypeError, ValueError):
        return None
    parents: dict[int, tuple[ast.AST, str, int | None]] = {}
    for parent in ast.walk(tree):
        for field_name, value in ast.iter_fields(parent):
            if isinstance(value, list):
                for index, child in enumerate(value):
                    if isinstance(child, ast.AST):
                        parents[id(child)] = (parent, field_name, index)
            elif isinstance(value, ast.AST):
                parents[id(value)] = (parent, field_name, None)

    lines = source.splitlines(keepends=True)
    requested_line = finding.get("line_number") if isinstance(finding, dict) else getattr(finding, "line_number", None)
    loops = [node for node in ast.walk(tree) if isinstance(node, ast.For) and not node.orelse and len(node.body) == 1
             and (requested_line is None or node.lineno <= requested_line <= (node.end_lineno or node.lineno))]
    for loop in loops:
        operation = loop.body[0]
        if not isinstance(operation, ast.AugAssign) or not isinstance(operation.op, ast.Add) or not isinstance(operation.target, ast.Name):
            continue
        accumulator = operation.target.id
        target_names = _target_names(loop.target)
        if not target_names or accumulator in target_names or not _pure_join_expression(operation.value, target_names):
            continue
        if any(isinstance(node, ast.Name) and node.id == accumulator and isinstance(node.ctx, ast.Load)
               for node in ast.walk(operation.value)):
            continue
        unit = _scope_unit(tree, loop)
        if used_outside(unit, loop, target_names):
            continue

        parent_entry = parents.get(id(loop))
        if parent_entry is None or parent_entry[2] is None:
            continue
        body = getattr(parent_entry[0], parent_entry[1])
        loop_index = parent_entry[2]
        if loop_index == 0:
            continue
        init = body[loop_index - 1]
        if not isinstance(init, ast.Assign) or len(init.targets) != 1 or not isinstance(init.targets[0], ast.Name) or init.targets[0].id != accumulator:
            continue
        if not isinstance(init.value, ast.Constant) or not isinstance(init.value.value, str):
            continue
        if init.end_lineno is None or loop.end_lineno is None or init.lineno >= loop.lineno:
            continue
        if _contains_comment(source, init.lineno, loop.end_lineno):
            continue

        # Avoid changing bindings assigned elsewhere and then observed later.
        if used_outside(unit, loop, target_names):
            continue

        iterable = loop.iter
        # dict.items() is required for tuple unpacking and is the only method
        # call accepted here; arbitrary iterator calls can have side effects.
        if isinstance(iterable, ast.Call):
            if not (isinstance(iterable.func, ast.Attribute) and iterable.func.attr == "items"
                    and isinstance(iterable.func.value, ast.Name) and not iterable.args and not iterable.keywords):
                continue
        elif not isinstance(iterable, ast.Name):
            continue

        generator = ast.GeneratorExp(
            elt=operation.value,
            generators=[ast.comprehension(target=loop.target, iter=iterable, ifs=[], is_async=0)],
        )
        joined = ast.Call(
            func=ast.Attribute(value=ast.Constant(value=""), attr="join", ctx=ast.Load()),
            args=[generator], keywords=[],
        )
        replacement = ast.Assign(
            targets=[ast.Name(id=accumulator, ctx=ast.Store())],
            value=ast.BinOp(left=ast.Constant(value=init.value.value), op=ast.Add(), right=joined),
        )
        ast.copy_location(replacement, init)
        ast.fix_missing_locations(replacement)

        start_index = init.lineno - 1
        stop_index = loop.end_lineno
        if start_index < 0 or stop_index > len(lines):
            continue
        init_prefix = lines[start_index].encode("utf-8")[:init.col_offset]
        init_suffix = lines[init.lineno - 1].encode("utf-8")[init.end_col_offset:]
        loop_suffix = lines[loop.end_lineno - 1].encode("utf-8")[loop.end_col_offset:]
        if init_prefix.strip() or init_suffix.strip() or loop_suffix.strip():
            # Replacing physical lines is only safe when these statements own
            # their complete lines (no semicolon siblings or trailing text).
            continue
        original_block = "".join(lines[start_index:stop_index])
        init_line = lines[start_index]
        indent = init_line[:len(init_line) - len(init_line.lstrip(" \t"))]
        newline = "\r\n" if "\r\n" in original_block else "\n" if "\n" in original_block else ""
        new_block = indent + ast.unparse(replacement) + newline
        new_source = "".join(lines[:start_index]) + new_block + "".join(lines[stop_index:])
        diff = "".join(difflib.unified_diff(
            original_block.splitlines(keepends=True), new_block.splitlines(keepends=True),
            fromfile="original", tofile="suggested",
        ))
        return {"new_source": new_source, "diff": diff, "transformer": "concat_to_join"}
    return None


def concat_to_join_refusal(source: str, finding: Any = None) -> str:
    """Explain why the registered concat rewrite cannot safely apply."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, TypeError, ValueError):
        return "The source does not parse as Python."
    requested_line = finding.get("line_number") if isinstance(finding, dict) else getattr(finding, "line_number", None)
    loops = [node for node in ast.walk(tree) if isinstance(node, (ast.For, ast.AsyncFor, ast.While))
             and (requested_line is None or node.lineno <= requested_line <= (node.end_lineno or node.lineno))]
    if not loops:
        return "The finding is not inside a supported loop."
    loop = min(loops, key=lambda node: (node.end_lineno or node.lineno) - node.lineno)
    if isinstance(loop, ast.While):
        return "while loops are not supported by concat_to_join."
    if isinstance(loop, ast.AsyncFor):
        return "Async iteration cannot be rewritten as a synchronous join."
    if loop.orelse:
        return "for...else loops are not supported because the else block has separate behavior."
    if len(loop.body) != 1 or not isinstance(loop.body[0], ast.AugAssign) or not isinstance(loop.body[0].op, ast.Add) or not isinstance(loop.body[0].target, ast.Name):
        return "The loop body is not a single string-concatenation update."
    operation = loop.body[0]
    accumulator = operation.target.id
    if any(isinstance(node, ast.Name) and node.id == accumulator and isinstance(node.ctx, ast.Load) for node in ast.walk(operation.value)):
        return "The accumulator is read while updating it inside the loop."
    target_names = _target_names(loop.target)
    if used_outside(_scope_unit(tree, loop), loop, target_names):
        return "A loop target is read elsewhere in its enclosing unit; its post-loop binding could change."
    parents: dict[int, tuple[ast.AST, str, int | None]] = {}
    for parent in ast.walk(tree):
        for field_name, value in ast.iter_fields(parent):
            if isinstance(value, list):
                for index, child in enumerate(value):
                    if isinstance(child, ast.AST):
                        parents[id(child)] = (parent, field_name, index)
    parent = parents.get(id(loop))
    if parent is None or parent[2] is None or parent[2] == 0:
        return "No immediately preceding string initializer was found in the same block."
    initializer = getattr(parent[0], parent[1])[parent[2] - 1]
    if not isinstance(initializer, ast.Assign) or len(initializer.targets) != 1 or not isinstance(initializer.targets[0], ast.Name) or initializer.targets[0].id != accumulator:
        return "The accumulator must have an adjacent simple assignment before the loop."
    if not isinstance(initializer.value, ast.Constant) or not isinstance(initializer.value.value, str):
        return "The accumulator initializer must be a string literal."
    if _contains_comment(source, initializer.lineno, loop.end_lineno or loop.lineno):
        return "Comments in the replaced initializer-to-loop region are preserved by refusing the rewrite."
    if not _pure_join_expression(operation.value, target_names):
        return "The concatenated expression has unsupported names, calls, or side effects."
    if not isinstance(loop.iter, ast.Name) and not (
        isinstance(loop.iter, ast.Call) and isinstance(loop.iter.func, ast.Attribute)
        and loop.iter.func.attr == "items" and isinstance(loop.iter.func.value, ast.Name)
        and not loop.iter.args and not loop.iter.keywords
    ):
        return "The loop iterable is not a simple name or a plain dict.items() call."
    return "The candidate did not pass compilation, name, or analyzer checks."


LOOSE_TEMPLATE_RULES = {
    "EKB-COMP-001", "EKB-COMP-002", "EKB-COMP-003", "EKB-IO-001",
    "EKB-NET-001", "EKB-ASYNC-001", "EKB-MEM-001",
}


@lru_cache(maxsize=1)
def _energy_rule_recommendations() -> dict[str, str]:
    return {rule.id: rule.recommendation for rule in RuleLoader().load_default_rules()}


def _comment_fallback(original: str, start_line: int, finding_line: int, rule_id: str) -> str:
    """Insert one KB recommendation comment without changing original bytes."""
    rows = original.splitlines(keepends=True)
    relative_line = max(0, min(finding_line - start_line, len(rows) - 1))
    target = rows[relative_line]
    indent = target[:len(target) - len(target.lstrip(" \t"))]
    newline = "\r\n" if target.endswith("\r\n") else "\n" if target.endswith("\n") else "\r\n" if "\r\n" in original else "\n"
    recommendation = _energy_rule_recommendations().get(
        rule_id, "Review this code for an energy efficient implementation."
    ).replace("\r", " ").replace("\n", " ")
    comment = f"{indent}# Energy smell ({rule_id}): {recommendation}{newline}"
    rows.insert(relative_line, comment)
    return "".join(rows)


def _finding_value(finding: Any, key: str, default: Any = None) -> Any:
    return finding.get(key, default) if isinstance(finding, dict) else getattr(finding, key, default)


def _loose_template(source: str, finding: Any, rule_id: str) -> dict[str, str] | None:
    """Build a deterministic, compile-checked template for a flagged function."""
    try:
        tree = ast.parse(source)
        compile(tree, "<recommendation-template>", "exec")
    except (SyntaxError, TypeError, ValueError):
        return None
    line = _finding_value(finding, "line_number")
    try:
        line = int(line)
    except (TypeError, ValueError):
        line = 1
    functions = [node for node in ast.walk(tree)
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and node.lineno <= line <= (node.end_lineno or node.lineno)]
    function = min(functions, key=lambda n: (n.end_lineno or n.lineno) - n.lineno) if functions else None
    lines = source.splitlines(keepends=True)
    if not lines:
        return None
    if function:
        start = min([function.lineno, *(d.lineno for d in function.decorator_list)])
        end = function.end_lineno or function.lineno
    else:
        top_level = [node for node in tree.body if node.lineno <= line <= (node.end_lineno or node.lineno)]
        statement = min(top_level, key=lambda n: (n.end_lineno or n.lineno) - n.lineno) if top_level else None
        start = statement.lineno if statement else max(1, min(line, len(lines)))
        end = (statement.end_lineno or statement.lineno) if statement else start
    original = "".join(lines[start - 1:end])
    indent = lines[start - 1][:len(lines[start - 1]) - len(lines[start - 1].lstrip(" \t"))]
    newline = "\r\n" if "\r\n" in original else "\n"

    # Apply a concrete structural template when the local shape matches.
    replacement = original
    label = "loose_template"
    if function and rule_id == "EKB-COMP-001":
        rewritten_function = copy.deepcopy(function)
        lookup_found = False
        def optimize_block(statements: list[ast.stmt]) -> bool:
            for outer_index, outer in enumerate(statements):
                if not isinstance(outer, ast.For) or outer.orelse or not isinstance(outer.target, ast.Name):
                    continue
                for inner_index, inner in enumerate(outer.body):
                    if not isinstance(inner, ast.For) or inner.orelse or len(inner.body) != 1 or not isinstance(inner.body[0], ast.If):
                        continue
                    condition = inner.body[0]
                    test = condition.test
                    if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)
                            and len(test.comparators) == 1 and isinstance(test.left, ast.Name)
                            and isinstance(test.comparators[0], ast.Name) and isinstance(inner.target, ast.Name)):
                        continue
                    if {test.left.id, test.comparators[0].id} != {outer.target.id, inner.target.id}:
                        continue
                    lookup_name = "_carbon_lookup"
                    names = {n.id for n in ast.walk(rewritten_function) if isinstance(n, ast.Name)}
                    suffix = 1
                    while lookup_name in names:
                        lookup_name = f"_carbon_lookup_{suffix}"
                        suffix += 1
                    lookup = ast.Assign(
                        targets=[ast.Name(id=lookup_name, ctx=ast.Store())],
                        value=ast.Call(func=ast.Name(id="set", ctx=ast.Load()), args=[copy.deepcopy(inner.iter)], keywords=[]),
                    )
                    ast.copy_location(lookup, outer)
                    membership = ast.If(
                        test=ast.Compare(left=copy.deepcopy(outer.target), ops=[ast.In()], comparators=[ast.Name(id=lookup_name, ctx=ast.Load())]),
                        body=condition.body, orelse=[],
                    )
                    ast.copy_location(membership, inner)
                    outer.body[inner_index] = membership
                    statements.insert(outer_index, lookup)
                    return True
            for statement in statements:
                for field_value in ast.iter_fields(statement):
                    if isinstance(field_value, list) and all(isinstance(item, ast.stmt) for item in field_value) and optimize_block(field_value):
                        return True
            return False
        lookup_found = optimize_block(rewritten_function.body)
        if lookup_found:
            ast.fix_missing_locations(rewritten_function)
            rendered = ast.unparse(rewritten_function)
            replacement = "\n".join((indent + row if row else row) for row in rendered.splitlines()) + newline
            label = "template_nested_lookup_set"
    if function and rule_id == "EKB-MEM-001":
        parents: dict[int, tuple[ast.AST, str, int]] = {}
        for parent_node in ast.walk(function):
            for field_name, field_value in ast.iter_fields(parent_node):
                if isinstance(field_value, list):
                    for index, child in enumerate(field_value):
                        if isinstance(child, ast.AST):
                            parents[id(child)] = (parent_node, field_name, index)
        for loop in ast.walk(function):
            if not isinstance(loop, ast.For) or loop.orelse or len(loop.body) != 1:
                continue
            append = loop.body[0]
            if not (isinstance(append, ast.Expr) and isinstance(append.value, ast.Call)
                    and isinstance(append.value.func, ast.Attribute) and append.value.func.attr == "append"
                    and isinstance(append.value.func.value, ast.Name) and len(append.value.args) == 1):
                continue
            entry = parents.get(id(loop))
            if entry is None or entry[2] == 0:
                continue
            statements = getattr(entry[0], entry[1])
            initializer = statements[entry[2] - 1]
            if not (isinstance(initializer, ast.Assign) and len(initializer.targets) == 1
                    and isinstance(initializer.targets[0], ast.Name)
                    and initializer.targets[0].id == append.value.func.value.id
                    and isinstance(initializer.value, (ast.List, ast.Call))
                    and (isinstance(initializer.value, ast.List) or
                         isinstance(initializer.value.func, ast.Name) and initializer.value.func.id == "list")):
                continue
            value = ast.ListComp(
                elt=copy.deepcopy(append.value.args[0]),
                generators=[ast.comprehension(target=copy.deepcopy(loop.target), iter=copy.deepcopy(loop.iter), ifs=[], is_async=0)],
            )
            statement = ast.Assign(targets=copy.deepcopy(initializer.targets), value=value)
            ast.fix_missing_locations(statement)
            local = original.splitlines(keepends=True)
            first = initializer.lineno - start
            last = loop.end_lineno - start + 1
            if 0 <= first < last <= len(local):
                stmt_indent = lines[initializer.lineno - 1][:len(lines[initializer.lineno - 1]) - len(lines[initializer.lineno - 1].lstrip(" \t"))]
                local[first:last] = [stmt_indent + ast.unparse(statement) + newline]
                replacement = "".join(local)
                label = "template_list_comprehension"
                break
    if function and rule_id == "EKB-IO-001":
        for loop in ast.walk(function):
            if not isinstance(loop, ast.For) or loop.orelse or len(loop.body) != 1 or not isinstance(loop.body[0], ast.With):
                continue
            with_node = loop.body[0]
            context = with_node.items[0].context_expr if with_node.items else None
            if not (isinstance(context, ast.Call) and isinstance(context.func, ast.Name) and context.func.id == "open"):
                continue
            local = original.splitlines(keepends=True)
            for_rel, with_rel = loop.lineno - start, with_node.lineno - start
            if not (0 <= for_rel < len(local) and 0 <= with_rel < len(local)):
                continue
            for_line = lines[loop.lineno - 1]
            with_line = lines[with_node.lineno - 1]
            for_indent = for_line[:len(for_line) - len(for_line.lstrip(" \t"))]
            with_indent = with_line[:len(with_line) - len(with_line.lstrip(" \t"))]
            local[for_rel:with_rel + 1] = [for_indent + with_line.lstrip(), with_indent + for_line.lstrip()]
            replacement = "".join(local)
            label = "template_open_outside_loop"
            break
    if function and rule_id == "EKB-COMP-002":
        for node in ast.walk(function):
            if not isinstance(node, ast.For) or node.orelse:
                continue
            assignment = next((stmt for stmt in node.body if isinstance(stmt, ast.Assign)), None)
            if assignment is None or not isinstance(assignment.value, ast.Constant):
                continue
            segment = ast.get_source_segment(source, assignment)
            loop_line = lines[node.lineno - 1]
            loop_indent = loop_line[:len(loop_line) - len(loop_line.lstrip(" \t"))]
            local = original.splitlines(keepends=True)
            relative_loop = node.lineno - start
            relative_assignment = assignment.lineno - start
            if segment and 0 <= relative_loop < len(local) and 0 <= relative_assignment < len(local):
                local.pop(relative_assignment)
                local.insert(relative_loop, loop_indent + segment.lstrip() + newline)
                replacement = "".join(local)
                label = "template_loop_invariant"
                break
    if function and rule_id == "EKB-COMP-003":
        if not any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "lru_cache" for d in function.decorator_list):
            definition = function.lineno - start
            text = original.splitlines(keepends=True)
            text.insert(max(0, definition), indent + "@functools.lru_cache(maxsize=None)" + newline)
            replacement = "".join(text)
            if not any(isinstance(n, (ast.Import, ast.ImportFrom)) and "functools" in (ast.get_source_segment(source, n) or "") for n in tree.body):
                replacement = "import functools" + newline + replacement
            label = "template_recursion_cache"
    if function and rule_id == "EKB-NET-001":
        net_calls = [n for n in ast.walk(function) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                     and isinstance(n.func.value, ast.Name) and n.func.value.id == "requests"
                     and n.func.attr in {"get", "post", "put", "patch", "delete", "head"}]
        loops = [n for n in ast.walk(function) if isinstance(n, (ast.For, ast.AsyncFor, ast.While))]
        if net_calls and loops and all(call.lineno >= min(loop.lineno for loop in loops) for call in net_calls):
            local = original.splitlines(keepends=True)
            first_loop = min(loops, key=lambda n: n.lineno)
            loop_rel = first_loop.lineno - start
            loop_line = lines[first_loop.lineno - 1]
            loop_indent = loop_line[:len(loop_line) - len(loop_line.lstrip(" \t"))]
            if 0 <= loop_rel < len(local):
                local.insert(loop_rel, loop_indent + "session = requests.Session()" + newline)
                replacement = re.sub(r"\brequests\.(get|post|put|patch|delete|head)\b", r"session.\1", "".join(local))
                label = "template_requests_session"
    if isinstance(function, ast.AsyncFunctionDef) and rule_id == "EKB-ASYNC-001":
        blocking = next((n for n in ast.walk(function) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                         and isinstance(n.func.value, ast.Name) and n.func.value.id in {"time", "subprocess"}
                         and n.func.attr in {"sleep", "run", "call", "check_call", "check_output"}), None)
        if blocking:
            call_text = ast.get_source_segment(source, blocking)
            if call_text:
                args_text = ", ".join([ast.unparse(blocking.func), *(ast.unparse(arg) for arg in blocking.args)])
                replacement_call = f"await asyncio.to_thread({args_text})"
                changed = original.replace(call_text, replacement_call, 1)
                if changed != original:
                    body_rel = function.body[0].lineno - start if function.body else function.lineno - start + 1
                    local = changed.splitlines(keepends=True)
                    fn_indent = lines[function.lineno - 1][:len(lines[function.lineno - 1]) - len(lines[function.lineno - 1].lstrip(" \t"))]
                    local.insert(max(0, body_rel), fn_indent + ("\t" if "\t" in fn_indent else "    ") + "import asyncio" + newline)
                    replacement = "".join(local)
                    label = "template_asyncio_to_thread"
    if replacement == original:
        replacement = _comment_fallback(original, start, line, rule_id)
        label = "template_comment_fallback"
    candidate_source = "".join(lines[:start - 1]) + replacement + "".join(lines[end:])
    try:
        ast.parse(candidate_source)
        compile(candidate_source, "<recommendation-template>", "exec")
    except (SyntaxError, TypeError, ValueError):
        replacement = _comment_fallback(original, start, line, rule_id)
        candidate_source = "".join(lines[:start - 1]) + replacement + "".join(lines[end:])
        try:
            ast.parse(candidate_source)
            compile(candidate_source, "<recommendation-template>", "exec")
        except (SyntaxError, TypeError, ValueError):
            return None
        label = "template_minimal_compile_safe"
    if candidate_source == source:
        return None
    return {
        "new_source": candidate_source,
        "diff": "".join(difflib.unified_diff(original.splitlines(keepends=True), replacement.splitlines(keepends=True), fromfile="original", tofile="suggested")),
        "transformer": label,
        "replacement_code": replacement,
        "original_code": original,
        "line_start": str(start),
        "line_end": str(end),
    }


def recommend(
    source: str,
    finding: Any = None,
    analyze_fn: Callable[[str], Any] | None = None,
) -> dict[str, str] | None:
    """Try the strict registered rewrite, then a local compile-checked template."""
    rule_id = (finding.get("rule_id") if isinstance(finding, dict) else getattr(finding, "rule_id", None)) or (
        finding if isinstance(finding, str) else "EKB-MEM-001"
    )
    selected = TRANSFORMER_REGISTRY.get(rule_id)
    line_number = finding.get("line_number") if isinstance(finding, dict) else getattr(finding, "line_number", None)
    try:
        line_number = int(line_number) if line_number is not None else None
    except (TypeError, ValueError):
        line_number = None
    cache_key = (hashlib.sha256(source.encode("utf-8", errors="replace")).hexdigest(), rule_id, line_number)
    if selected is not None and cache_key in _RECOMMENDATION_CACHE:
        cached = _RECOMMENDATION_CACHE[cache_key]
        if cached is not None:
            return dict(cached)
    try:
        candidate = selected(source, finding) if selected is not None else None
        if candidate is not None and passes_gate(source, candidate["new_source"], analyze_fn=analyze_fn):
            _RECOMMENDATION_CACHE[cache_key] = dict(candidate)
            return dict(candidate)
        if selected is not None:
            _RECOMMENDATION_CACHE[cache_key] = None
    except (KeyError, SyntaxError, TypeError, ValueError):
        pass
    return _loose_template(source, finding, rule_id)
