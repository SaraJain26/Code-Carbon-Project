import ast
from detector.context import DetectionContext
from detector.models import (
    Candidate,
    CandidateEvidence,
    EvidenceKind,
)
from knowledge import RuleConfidence


class RedundantComputationDetector:
    RULE_ID = "EKB-COMP-002"
    PURE_BUILTINS = {"abs", "all", "any", "bool", "float", "int", "len", "max", "min", "sum", "tuple"}

    @classmethod
    def _safe_builtin_call(cls, call: ast.Call) -> bool:
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

    def detect(self, context: DetectionContext) -> list[Candidate]:
        result = context.analysis_result
        candidates: list[Candidate] = []

        if not hasattr(result.module, "tree") or result.module.tree is None:
            return candidates

        tree = result.module.tree

        for loop_info in result.loops:
            loop_node = None
            for node in ast.walk(tree):
                if isinstance(node, (ast.For, ast.While, ast.AsyncFor)) and node.lineno == loop_info.line_number:
                    loop_node = node
                    break

            if loop_node is None or not isinstance(loop_node, (ast.For, ast.While)):
                continue

            loop_vars = set()
            if isinstance(loop_node, ast.For):
                for name_node in ast.walk(loop_node.target):
                    if isinstance(name_node, ast.Name):
                        loop_vars.add(name_node.id)
            for node in ast.walk(loop_node):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        for name_node in ast.walk(target):
                            if isinstance(name_node, ast.Name):
                                loop_vars.add(name_node.id)

            for stmt in loop_node.body:
                if isinstance(stmt, ast.Assign):
                    is_alloc = isinstance(stmt.value, (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp))
                    if is_alloc:
                        continue  # Handled by MemoryAllocationDetector (EKB-MEM-001)

                    is_invariant = True
                    for child in ast.walk(stmt.value):
                        if isinstance(child, ast.Name) and child.id in loop_vars:
                            is_invariant = False
                            break
                        if isinstance(child, ast.Call) and not self._safe_builtin_call(child):
                            is_invariant = False
                            break

                    if is_invariant:
                        lineno = getattr(stmt, "lineno", loop_info.line_number)
                        candidates.append(
                            Candidate.create(
                                rule_id=self.RULE_ID,
                                confidence=RuleConfidence(0.78),
                                message="Redundant computation in loop.",
                                evidence=[
                                    CandidateEvidence(
                                        kind=EvidenceKind.LOOP,
                                        source_file=result.module.source_file,
                                        line_number=lineno,
                                    )
                                ],
                            )
                        )

        return candidates
