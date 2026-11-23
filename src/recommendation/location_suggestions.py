"""Conservative, source-derived code suggestions for individual findings.

These suggestions do not participate in detection, ranking, or modeled scoring.
Only transformations with a small, mechanically verifiable shape are labelled
Suggested. Other locations receive a valid Python review note tied to the real
source names and never a fabricated example.
"""

from __future__ import annotations

import ast
import builtins
import copy
import difflib
import operator
import symtable
import textwrap
from typing import Any
from collections.abc import Callable
from .transformer import recommend

# Import roots with API patterns whose behavior is context dependent. Keep this
# table data-only so adding a library never adds a library-specific rewrite.
BY_DESIGN_REVIEW_PATTERNS: dict[str, tuple[str, ...]] = {
    "flask": ("route", "request", "session"),
    "django": ("transaction", "request", "QuerySet"),
    "fastapi": ("Depends", "BackgroundTasks"),
    "sqlalchemy": ("Session", "session", "commit", "execute"),
    "pandas": ("DataFrame", "Series", "read_csv"),
    "numpy": ("array", "ndarray", "vectorize"),
    "torch": ("Tensor", "no_grad", "autograd"),
    "requests": ("get", "post", "request", "Session"),
    "httpx": ("get", "post", "request", "AsyncClient"),
    "asyncio": ("create_task", "gather", "TaskGroup", "sleep"),
}

MAX_SOURCE_BYTES = 2_000_000


def _line_span(node: ast.AST) -> tuple[int, int]:
    return int(getattr(node, "lineno", 0) or 0), int(getattr(node, "end_lineno", 0) or 0)


def _contains_line(node: ast.AST, line: int) -> bool:
    start, end = _line_span(node)
    return start <= line <= (end or start)


def _names(node: ast.AST) -> set[str]:
    if isinstance(node, list):
        node = ast.Module(body=node, type_ignores=[])
    return {item.id for item in ast.walk(node) if isinstance(item, ast.Name)}


def _source(node: ast.AST, source: str) -> str:
    return ast.get_source_segment(source, node) or ""


def _changed_region(original: str, rewritten: str) -> tuple[int, int, str, str] | None:
    before = original.splitlines(keepends=True)
    after = rewritten.splitlines(keepends=True)
    changes = [opcode for opcode in difflib.SequenceMatcher(None, before, after, autojunk=False).get_opcodes() if opcode[0] != "equal"]
    if len(changes) != 1:
        return None
    _, old_start, old_end, new_start, new_end = changes[0]
    original_region = "".join(before[old_start:old_end])
    replacement_region = "".join(after[new_start:new_end])
    if not original_region or not replacement_region:
        return None
    return old_start + 1, old_end, original_region, replacement_region


def _constant_expression(node: ast.AST) -> bool:
    try:
        value = ast.literal_eval(node)
    except Exception:
        value = None
    if isinstance(value, (str, bytes, int, float, complex, bool, tuple, list, set, dict)):
        return True
    binary = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
    unary = {ast.UAdd: operator.pos, ast.USub: operator.neg, ast.Not: operator.not_}
    def evaluate(item: ast.AST) -> Any:
        if isinstance(item, ast.Constant): return item.value
        if isinstance(item, ast.BinOp) and type(item.op) in binary: return binary[type(item.op)](evaluate(item.left), evaluate(item.right))
        if isinstance(item, ast.UnaryOp) and type(item.op) in unary: return unary[type(item.op)](evaluate(item.operand))
        raise ValueError("expression is not literal-only")
    try:
        evaluate(node)
        return True
    except Exception:
        return False


def _find_loop(tree: ast.AST, line: int) -> ast.For | ast.AsyncFor | ast.While | None:
    candidates = [node for node in ast.walk(tree) if isinstance(node, (ast.For, ast.AsyncFor, ast.While)) and _contains_line(node, line)]
    return min(candidates, key=lambda node: _line_span(node)[1] - _line_span(node)[0]) if candidates else None


def _exact_rewrite(tree: ast.AST, source: str, line: int, rule_id: str) -> tuple[str, str] | None:
    """Return a conservative AST-shaped rewrite and its confidence rationale."""
    loop = _find_loop(tree, line)
    if rule_id == "EKB-COMP-001":
        loops = [node for node in ast.walk(tree) if isinstance(node, (ast.For, ast.AsyncFor)) and _contains_line(node, line)]
        if loops:
            loop = max(loops, key=lambda node: _line_span(node)[1] - _line_span(node)[0])
    if loop is None:
        return None

    # The current proven transformations are synchronous and require simple
    # control flow. Async iterators, nested scopes, and control transfers need
    # dedicated semantic proofs; they stay review-only.
    if isinstance(loop, ast.AsyncFor):
        return None
    if any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef))
           for statement in loop.body for node in ast.walk(statement)):
        return None
    if any(isinstance(node, (ast.Break, ast.Continue, ast.Return, ast.Yield, ast.YieldFrom,
                             ast.Global, ast.Nonlocal, ast.Await))
           for statement in loop.body for node in ast.walk(statement)):
        return None

    if rule_id == "EKB-COMP-001" and isinstance(loop, (ast.For, ast.AsyncFor)) and len(loop.body) == 1:
        inner = loop.body[0]
        if isinstance(inner, ast.For) and isinstance(loop.iter, ast.Name) and isinstance(inner.iter, ast.Name) and isinstance(inner.target, ast.Name) and inner.iter.id == loop.target.id and not loop.orelse and not inner.orelse:
            outer_names = {name.id for name in ast.walk(loop.target) if isinstance(name, ast.Name)}
            if not outer_names.intersection(_names(inner.body)) and not _name_used_outside(tree, loop, outer_names):
                used = _names(tree)
                alias = "_itertools_ekb"
                suffix = 2
                while alias in used:
                    alias = f"_itertools_ekb_{suffix}"
                    suffix += 1
                target = inner.target
                flat_iter = ast.Call(func=ast.Attribute(value=ast.Attribute(value=ast.Name(id=alias, ctx=ast.Load()), attr="chain", ctx=ast.Load()), attr="from_iterable", ctx=ast.Load()), args=[loop.iter], keywords=[])
                rewritten = ast.For(target=target, iter=flat_iter, body=inner.body, orelse=[], type_comment=None)
                module = ast.Module(body=[ast.Import(names=[ast.alias(name="itertools", asname=alias)]), rewritten], type_ignores=[])
                ast.fix_missing_locations(module)
                return ast.unparse(module), f"Flattened `{loop.iter.id}` once with itertools.chain.from_iterable while preserving iteration order."

        membership = _membership_rewrite(loop, tree)
        if membership:
            return membership

    # EKB-COMP-002: hoist literal-only invariant assignments. Constant
    # expressions are evaluated safely before display and cannot read mutated
    # state or perform calls.
    if rule_id == "EKB-COMP-002" and isinstance(loop, (ast.For, ast.AsyncFor, ast.While)):
        for statement in loop.body:
            if isinstance(statement, ast.Assign) and _constant_expression(statement.value):
                if not (_names(statement.value) & _names(loop.target if isinstance(loop, (ast.For, ast.AsyncFor)) else loop.test)):
                    body = [item for item in loop.body if item is not statement]
                    rewritten_loop = ast.For(loop.target, loop.iter, body, loop.orelse, type_comment=getattr(loop, "type_comment", None)) if isinstance(loop, ast.For) else (
                        ast.AsyncFor(loop.target, loop.iter, body, loop.orelse, type_comment=getattr(loop, "type_comment", None)) if isinstance(loop, ast.AsyncFor)
                        else ast.While(loop.test, body, loop.orelse)
                    )
                    module = ast.Module(body=[statement, rewritten_loop], type_ignores=[])
                    ast.fix_missing_locations(module)
                    return ast.unparse(module), "Hoisted a literal-only invariant assignment above its loop."

    # EKB-IO-001: hoist repeated file handle opening outside the loop
    if rule_id == "EKB-IO-001" and isinstance(loop, (ast.For, ast.AsyncFor, ast.While)):
        if len(loop.body) == 1 and isinstance(loop.body[0], ast.With) and len(loop.body[0].items) == 1:
            with_item = loop.body[0].items[0]
            expr = with_item.context_expr
            if isinstance(expr, ast.Call) and (
                (isinstance(expr.func, ast.Name) and expr.func.id == "open")
                or (isinstance(expr.func, ast.Attribute) and expr.func.attr == "open")
            ):
                loop_vars = _names(loop.target if isinstance(loop, (ast.For, ast.AsyncFor)) else loop.test)
                if _names(expr).isdisjoint(loop_vars):
                    inner_loop = ast.For(
                        target=loop.target,
                        iter=loop.iter,
                        body=loop.body[0].body,
                        orelse=loop.orelse,
                        type_comment=getattr(loop, "type_comment", None),
                    ) if isinstance(loop, ast.For) else (
                        ast.AsyncFor(
                            target=loop.target,
                            iter=loop.iter,
                            body=loop.body[0].body,
                            orelse=loop.orelse,
                            type_comment=getattr(loop, "type_comment", None),
                        ) if isinstance(loop, ast.AsyncFor)
                        else ast.While(test=loop.test, body=loop.body[0].body, orelse=loop.orelse)
                    )
                    rewritten_with = ast.With(items=loop.body[0].items, body=[inner_loop])
                    ast.fix_missing_locations(rewritten_with)
                    return ast.unparse(rewritten_with), "Opened the file handle once outside the loop and reused it across iterations."

    # EKB-MEM-001: convert a simple list accumulation loop to a comprehension
    # when it is the sole loop body and the collection is initialized just
    # before that loop in the same function/module block.
    if rule_id == "EKB-MEM-001" and isinstance(loop, (ast.For, ast.AsyncFor)) and len(loop.body) == 1 and isinstance(loop.body[0], ast.Expr):
        append = loop.body[0].value
        if isinstance(append, ast.Call) and isinstance(append.func, ast.Attribute) and append.func.attr == "append" and isinstance(append.func.value, ast.Name) and len(append.args) == 1:
            target_name = append.func.value.id
            parent_body = _parent_body(tree, loop)
            index = parent_body.index(loop) if parent_body and loop in parent_body else -1
            if index > 0 and isinstance(parent_body[index - 1], ast.Assign):
                init = parent_body[index - 1]
                if any(isinstance(target, ast.Name) and target.id == target_name for target in init.targets) and isinstance(init.value, ast.List) and not init.value.elts:
                    comp = ast.ListComp(elt=append.args[0], generators=[ast.comprehension(target=loop.target, iter=loop.iter, ifs=[], is_async=0)])
                    assign = ast.Assign(targets=[ast.Name(id=target_name, ctx=ast.Store())], value=comp)
                    ast.fix_missing_locations(assign)
                    return ast.unparse(assign), f"Replaced `{target_name}.append(...)` accumulation with a comprehension using the observed loop."

    # EKB-MEM-001: coalesce a loop that only concatenates each yielded string.
    if rule_id == "EKB-MEM-001" and isinstance(loop, (ast.For, ast.AsyncFor)) and len(loop.body) == 1 and isinstance(loop.body[0], ast.AugAssign):
        operation = loop.body[0]
        if isinstance(operation.op, ast.Add) and isinstance(operation.target, ast.Name) and isinstance(loop.target, ast.Name) and isinstance(loop.iter, ast.Name) and _names(operation.value) == {loop.target.id}:
            parent_body = _parent_body(tree, loop)
            index = parent_body.index(loop) if parent_body and loop in parent_body else -1
            if index > 0 and isinstance(parent_body[index - 1], ast.Assign):
                init = parent_body[index - 1]
                if any(isinstance(target, ast.Name) and target.id == operation.target.id for target in init.targets) and isinstance(init.value, ast.Constant) and init.value.value == "":
                    joined = ast.Call(func=ast.Attribute(value=ast.Constant(""), attr="join", ctx=ast.Load()), args=[loop.iter], keywords=[])
                    assign = ast.AugAssign(target=operation.target, op=ast.Add(), value=joined)
                    ast.fix_missing_locations(assign)
                    return ast.unparse(assign), f"Joined the observed `{loop.iter.id}` values once before appending them to `{operation.target.id}`."

    return None


def _name_used_outside(tree: ast.AST, loop: ast.AST, names: set[str]) -> bool:
    for node in ast.walk(tree):
        if node is loop or _is_descendant(node, loop):
            continue
        if isinstance(node, ast.Name) and node.id in names:
            return True
    return False


def _is_descendant(node: ast.AST, ancestor: ast.AST) -> bool:
    return any(child is node for child in ast.walk(ancestor))


def _membership_rewrite(outer: ast.For | ast.AsyncFor | ast.While, tree: ast.AST) -> tuple[str, str] | None:
    if not isinstance(outer, ast.For) or len(outer.body) != 1 or not isinstance(outer.body[0], ast.For):
        return None
    inner = outer.body[0]
    if not isinstance(outer.target, ast.Name) or not isinstance(inner.target, ast.Name) or not isinstance(outer.iter, ast.Name) or not isinstance(inner.iter, ast.Name):
        return None
    if outer.orelse or inner.orelse or len(inner.body) != 1 or not isinstance(inner.body[0], ast.If) or inner.body[0].orelse:
        return None
    condition = inner.body[0]
    test = condition.test
    if not isinstance(test, ast.Compare) or len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return None
    left, right = test.left, test.comparators[0]
    if not ((isinstance(left, ast.Name) and left.id == outer.target.id and isinstance(right, ast.Name) and right.id == inner.target.id) or (isinstance(right, ast.Name) and right.id == outer.target.id and isinstance(left, ast.Name) and left.id == inner.target.id)):
        return None
    # A multimap preserves duplicate matches and inner iteration order.
    used = _names(tree)
    index_name = "_matches_by_key"
    suffix = 2
    while index_name in used:
        index_name = f"_matches_by_key_{suffix}"
        suffix += 1
    key = ast.Name(id=inner.target.id, ctx=ast.Load())
    init = ast.Assign(targets=[ast.Name(id=index_name, ctx=ast.Store())], value=ast.Dict(keys=[], values=[]))
    append = ast.Expr(value=ast.Call(func=ast.Attribute(value=ast.Call(func=ast.Attribute(value=ast.Name(id=index_name, ctx=ast.Load()), attr="setdefault", ctx=ast.Load()), args=[key, ast.List(elts=[], ctx=ast.Load())], keywords=[]), attr="append", ctx=ast.Load()), args=[key], keywords=[]))
    index_loop = ast.For(target=inner.target, iter=inner.iter, body=[append], orelse=[])
    
    if (
        len(condition.body) == 1
        and isinstance(condition.body[0], ast.Expr)
        and isinstance(condition.body[0].value, ast.Call)
        and isinstance(condition.body[0].value.func, ast.Attribute)
        and condition.body[0].value.func.attr == "append"
        and len(condition.body[0].value.args) == 1
        and isinstance(condition.body[0].value.args[0], ast.Name)
        and condition.body[0].value.args[0].id == inner.target.id
    ):
        acc = condition.body[0].value.func.value
        extend_call = ast.Expr(value=ast.Call(
            func=ast.Attribute(value=acc, attr="extend", ctx=ast.Load()),
            args=[ast.Call(
                func=ast.Attribute(value=ast.Name(id=index_name, ctx=ast.Load()), attr="get", ctx=ast.Load()),
                args=[ast.Name(id=outer.target.id, ctx=ast.Load()), ast.Tuple(elts=[], ctx=ast.Load())],
                keywords=[]
            )],
            keywords=[]
        ))
        rewritten_outer = ast.For(target=outer.target, iter=outer.iter, body=[extend_call], orelse=[])
    else:
        lookup = ast.Call(func=ast.Attribute(value=ast.Name(id=index_name, ctx=ast.Load()), attr="get", ctx=ast.Load()), args=[ast.Name(id=outer.target.id, ctx=ast.Load()), ast.Tuple(elts=[], ctx=ast.Load())], keywords=[])
        matched_loop = ast.For(target=inner.target, iter=lookup, body=condition.body, orelse=[])
        rewritten_outer = ast.For(target=outer.target, iter=outer.iter, body=[matched_loop], orelse=[])

    module = ast.Module(body=[init, index_loop, rewritten_outer], type_ignores=[])
    ast.fix_missing_locations(module)
    return ast.unparse(module), f"Built a lookup from `{inner.iter.id}` once and retained matching rows in their original order."


def _parent_body(tree: ast.AST, target: ast.AST) -> list[ast.stmt] | None:
    for parent in ast.walk(tree):
        body = getattr(parent, "body", None)
        if isinstance(body, list) and target in body:
            return body
    return None


def _review_reason(rule_id: str, code: str, line: int) -> str:
    compact = code.strip()
    if rule_id == "EKB-NET-001":
        return "Request freshness, retries, ordering, and rate limits depend on the client and service contract; review before batching or caching."
    if rule_id == "EKB-IO-001" and "open(" not in compact:
        return "The flagged line is not an open/read/write call; it may be a helper reached from elsewhere."
    if rule_id == "EKB-COMP-001":
        return "Nested-loop changes can affect iteration order, duplicate handling, and loop-variable bindings; no safe rewrite was proven."
    if rule_id == "EKB-COMP-002":
        return "Hoisting can bind a variable even when the loop runs zero times; evaluation count, exceptions, and scope are not proven safe."
    if rule_id in {"EKB-IO-001", "EKB-IO-002"}:
        return "Moving file access can change file position, truncation, closing, and error timing; no safe rewrite was proven."
    if rule_id == "EKB-NET-001":
        return "Batching or reusing a connection depends on the actual client API and request freshness requirements."
    if rule_id == "EKB-COMP-003":
        return "An iterative rewrite needs the real base case and return semantics; memoize only when the function is pure."
    if rule_id == "EKB-MEM-001":
        return "The value may need independent ownership each iteration; confirm consumers do not retain or mutate it."
    return f"Review the operation reported at line {line}; preserve behavior before applying a change."


def _framework_review_reason(tree: ast.AST, rule_id: str) -> str | None:
    imported: dict[str, set[str]] = {}
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                imported.setdefault(root, set()).add(alias.asname or root)
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".", 1)[0]
            imported.setdefault(root, set()).update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            used.add(node.attr)
    matched = [root for root, symbols in imported.items()
               if root in BY_DESIGN_REVIEW_PATTERNS
               and bool((symbols | set(BY_DESIGN_REVIEW_PATTERNS[root])) & used)]
    if matched and rule_id in {"EKB-COMP-001", "EKB-COMP-002", "EKB-IO-001", "EKB-IO-002", "EKB-MEM-001", "EKB-NET-001"}:
        return "Imported framework or library APIs may depend on their documented side effects; review this finding in that context."
    return None


def build_location_suggestions(
    source_code: str,
    findings: list[dict[str, Any]],
    fixes: list[dict[str, Any]] | None = None,
    analyzer=None,
    test_runner: Callable[[str], bool] | None = None,
) -> list[dict[str, Any]]:
    """Build gated, source-grounded replacements; unsafe locations have no replacement."""
    if not isinstance(source_code, str):
        source_code = ""
    if len(source_code.encode("utf-8", errors="replace")) > MAX_SOURCE_BYTES:
        return [{"rule_id": str(f.get("rule_id") or "UNKNOWN"), "line_number": f.get("line_number"),
                 "line_start": f.get("line_number"), "line_end": f.get("line_number"),
                 "original_code": "", "replacement_code": None, "confidence": "No safe rewrite",
                 "status": "no_safe_rewrite", "reason": "Source exceeds the 2 MB recommendation limit; analyze a smaller file.",
                 "ai_unavailable": True} for f in findings]
    lines = source_code.splitlines()
    try:
        tree = ast.parse(source_code)
    except (SyntaxError, ValueError, TypeError):
        tree = ast.Module(body=[], type_ignores=[])
    fixes = fixes or []
    suggestions: list[dict[str, Any]] = []
    for finding in findings:
        rule_id = str(finding.get("rule_id") or "UNKNOWN")
        line = int(finding.get("line_number") or 0)
        start = max(1, line - 3) if line else 1
        end = min(len(lines), line + 3) if line else min(len(lines), 7)
        original = "\n".join(lines[start - 1:end]).strip("\n") or ""
        loop = _find_loop(tree, line) if line else None
        if rule_id == "EKB-COMP-001" and line:
            outer_loops = [node for node in ast.walk(tree) if isinstance(node, (ast.For, ast.AsyncFor)) and _contains_line(node, line)]
            if outer_loops:
                loop = max(outer_loops, key=lambda node: _line_span(node)[1] - _line_span(node)[0])
        original_block = _source(loop, source_code) if loop else original
        suggestion_start = int(getattr(loop, "lineno", start)) if loop else start
        suggestion_end = int(getattr(loop, "end_lineno", end)) if loop else end
        confidence = "No safe rewrite"
        status = "no_safe_rewrite"
        replacement = ""
        ai_unavailable = True
        reason = _framework_review_reason(tree, rule_id) or _review_reason(rule_id, lines[line - 1] if 0 < line <= len(lines) else "", line)
        diff_text = None
        transformer_name = None
        candidate = recommend(source_code, finding, analyzer)
        if candidate:
            if candidate.get("replacement_code") and candidate["transformer"].startswith("template_"):
                changed = (
                    int(candidate.get("line_start", 1)),
                    int(candidate.get("line_end", 1)),
                    candidate.get("original_code", ""),
                    candidate["replacement_code"],
                )
            else:
                changed = _changed_region(source_code, candidate["new_source"])
            if changed:
                line_start, line_end, original_block, replacement = changed
                suggestion_start, suggestion_end = line_start, line_end
                diff_text = candidate["diff"]
                transformer_name = candidate["transformer"]
                confidence, status = ("Verified", "verified") if not transformer_name.startswith("template_") else ("Template", "template")
                if status == "verified":
                    reason = "Registered transformer passed the syntax, name, and analyzer gate."
                else:
                    reason = f"{reason} Deterministic local template; compile-checked, review behavior before applying."
            elif candidate.get("replacement_code"):
                replacement = candidate["replacement_code"]
                original_block = candidate.get("original_code", original_block)
                suggestion_start = int(candidate.get("line_start", suggestion_start))
                suggestion_end = int(candidate.get("line_end", suggestion_end))
                transformer_name = candidate["transformer"]
                confidence, status = "Template", "template"
                reason = f"{reason} Deterministic local template; compile-checked, review behavior before applying."
        elif rule_id == "EKB-MEM-001":
            from src.recommendation.transformer import concat_to_join_refusal
            reason = concat_to_join_refusal(source_code, finding)
        matching_fix = next((fix for fix in fixes if fix.get("rule_id") == rule_id and fix.get("is_auto_applied") and fix.get("replacement_code") and (fix.get("line_number") == line or (int(fix.get("line_start") or 0) <= line <= int(fix.get("line_end") or 0)))), None)
        if matching_fix and rule_id != "EKB-MEM-001" and not replacement and test_runner:
            candidate_text = str(matching_fix["replacement_code"]).strip()
            if loop and _passes_block_gate(original_block, candidate_text):
                rewritten_source = _replace_node_in_module(tree, loop, candidate_text) or _replace_source_block(source_code, loop, candidate_text)
                tests_pass = test_runner(rewritten_source)
                if rewritten_source and tests_pass and (analyzer is None or _passes_file_gate(source_code, rewritten_source, rule_id, findings, analyzer)):
                    replacement = candidate_text
                    confidence, status = "Verified", "verified"
                    reason = "Auto-applied AST change passed re-analysis."
        if not replacement and rule_id != "EKB-MEM-001":
            candidate = _exact_rewrite(tree, source_code, line, rule_id) if loop and rule_id != "EKB-MEM-001" and test_runner else None
            if candidate and analyzer:
                candidate_text, candidate_reason = candidate
                rewritten_source = _replace_node_in_module(tree, loop, candidate_text)
                tests_pass = bool(rewritten_source and test_runner(rewritten_source))
                if rewritten_source and tests_pass and _passes_block_gate(original_block, candidate_text) and _passes_file_gate(source_code, rewritten_source, rule_id, findings, analyzer):
                    replacement = candidate_text
                    reason = candidate_reason
                    confidence, status = "Suggested", "suggested"
                else:
                    reason = "The AST rewrite did not pass syntax, statement-change, or analyzer re-checks."
            elif not analyzer:
                reason = "The analyzer re-check is unavailable, so this candidate cannot be shown as a recommendation."
        if status == "no_safe_rewrite" and not reason:
            reason = "No candidate passed syntax, statement-change, analyzer, and undefined-name checks."
        suggestions.append({
            "rule_id": rule_id,
            "line_number": line or None,
            "line_start": suggestion_start,
            "line_end": suggestion_end,
            "original_code": original_block or original,
            "replacement_code": replacement or None,
            "original": original_block or original,
            "replacement": replacement or None,
            "confidence": confidence,
            "status": status,
            "reason": reason,
            "ai_unavailable": ai_unavailable,
            "diff": diff_text,
            "transformer": transformer_name,
        })
    return suggestions


def _passes_block_gate(original: str, replacement: str) -> bool:
    try:
        before = ast.parse(textwrap.dedent(original))
        after = ast.parse(textwrap.dedent(replacement))
    except SyntaxError:
        return False
    before_ast = ast.dump(before, include_attributes=False)
    after_ast = ast.dump(after, include_attributes=False)
    if before_ast == after_ast:
        return False
    before_statements = [ast.dump(node, include_attributes=False) for node in before.body if isinstance(node, ast.stmt)]
    after_statements = [ast.dump(node, include_attributes=False) for node in after.body if isinstance(node, ast.stmt)]
    return before_statements != after_statements


def _replace_node_in_module(tree: ast.AST, target: ast.AST, replacement: str) -> str | None:
    try:
        rewritten = copy.deepcopy(tree)
        candidate_nodes = ast.parse(textwrap.dedent(replacement)).body
    except SyntaxError:
        return None
    target_span = _line_span(target)
    for node in ast.walk(rewritten):
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        for index, statement in enumerate(body):
            if type(statement) is type(target) and _line_span(statement) == target_span:
                body[index:index + 1] = copy.deepcopy(candidate_nodes)
                try:
                    ast.fix_missing_locations(rewritten)
                    result = ast.unparse(rewritten)
                    ast.parse(result)
                    compile(result, "<suggestion>", "exec")
                    return result
                except (SyntaxError, ValueError, TypeError):
                    return None
    return None


def _finding_scores(findings: list[dict[str, Any]]) -> tuple[dict[str, int], dict[str, float]]:
    counts: dict[str, int] = {}
    confidences: dict[str, float] = {}
    for finding in findings:
        rule = str(finding.get("rule_id") or "UNKNOWN")
        conf_raw = finding.get("confidence")
        if isinstance(conf_raw, dict):
            conf = float(conf_raw.get("value", 1.0))
        elif isinstance(conf_raw, (int, float)):
            conf = float(conf_raw)
        else:
            conf = 1.0
        counts[rule] = counts.get(rule, 0) + 1
        confidences[rule] = confidences.get(rule, 0.0) + conf
    return counts, confidences


def _undefined_names(source: str) -> set[str]:
    try:
        table = symtable.symtable(source, "<suggestion>", "exec")
    except SyntaxError:
        return {"<syntax>"}
    unresolved: set[str] = set()
    builtin_names = set(dir(builtins))
    def visit(scope) -> None:
        for symbol in scope.get_symbols():
            is_param = getattr(symbol, "is_parameter", lambda: False)()
            if (
                symbol.is_referenced()
                and not symbol.is_assigned()
                and not symbol.is_imported()
                and not is_param
                and symbol.get_name() not in builtin_names
            ):
                unresolved.add(symbol.get_name())
        for child in scope.get_children():
            visit(child)
    visit(table)
    return unresolved


def _passes_file_gate(before: str, after: str, rule_id: str, findings: list[dict[str, Any]], analyzer) -> bool:
    try:
        ast.parse(after)
        compile(after, "<suggestion>", "exec")
        after_findings = analyzer(after)
    except Exception:
        return False
    before_counts, before_conf = _finding_scores(findings)
    after_counts, after_conf = _finding_scores(after_findings or [])
    reduced = (
        after_counts.get(rule_id, 0) < before_counts.get(rule_id, 0)
        or (
            after_counts.get(rule_id, 0) == before_counts.get(rule_id, 0)
            and round(after_conf.get(rule_id, 0.0), 3) < round(before_conf.get(rule_id, 0.0), 3)
        )
    )
    if not reduced:
        return False
    for r in after_counts:
        if r != rule_id:
            if after_counts[r] > before_counts.get(r, 0):
                return False
            if round(after_conf.get(r, 0.0), 3) > round(before_conf.get(r, 0.0), 3):
                return False
    return _undefined_names(after).issubset(_undefined_names(before))


def _replace_source_block(source: str, node: ast.AST, replacement: str) -> str | None:
    start, end = _line_span(node)
    lines = source.splitlines(keepends=True)
    if not start or not end or end > len(lines):
        return None
    indent = lines[start - 1][:len(lines[start - 1]) - len(lines[start - 1].lstrip())]
    replacement_lines = textwrap.dedent(replacement).splitlines()
    rendered = "".join((indent + row if row.strip() else row) + "\n" for row in replacement_lines)
    return "".join(lines[:start - 1]) + rendered + "".join(lines[end:])
