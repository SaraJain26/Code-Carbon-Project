import ast
from detector.context import DetectionContext
from detector.models import (
    Candidate,
    CandidateEvidence,
    EvidenceKind,
)
from knowledge import RuleConfidence


def _is_sequence_op(node: ast.AST) -> bool:
    """Check if an AST node represents a sequence, collection, or buffer allocation."""
    if isinstance(node, (ast.List, ast.Dict, ast.Set, ast.Tuple, ast.ListComp, ast.DictComp, ast.SetComp)):
        return True
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes, list, tuple, set)):
        return True
    return False


def _is_memory_allocation_expr(node: ast.AST) -> bool:
    """Determine if an AST expression creates a temporary memory allocation or buffer."""
    # 1. Direct collection literals or comprehensions
    if isinstance(node, (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)):
        return True

    # 2. Sequence multiplication BinOp: e.g. [0] * N, b"\x00" * N, [x for x in data] * 5
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        if _is_sequence_op(node.left) or _is_sequence_op(node.right):
            return True

    # 3. Explicit buffer constructors: bytearray(...), bytes(...)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id in ("bytearray", "bytes", "list", "dict", "set"):
            return True

    return False


class MemoryAllocationDetector:
    """
    Detects excessive temporary memory allocations inside loops (EKB-MEM-001).
    """
    RULE_ID = "EKB-MEM-001"

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

            for stmt in loop_node.body:
                # Check assignment RHS expressions
                if isinstance(stmt, ast.Assign) and _is_memory_allocation_expr(stmt.value):
                    lineno = getattr(stmt, "lineno", loop_info.line_number)
                    candidates.append(
                        Candidate.create(
                            rule_id=self.RULE_ID,
                            confidence=RuleConfidence(0.76),
                            message="Excessive temporary allocation in loop.",
                            evidence=[
                                CandidateEvidence(
                                    kind=EvidenceKind.LOOP,
                                    source_file=result.module.source_file,
                                    line_number=lineno,
                                )
                            ],
                        )
                    )
                # Check expression statements in loop body (e.g. bytearray(...) or [0]*1000 without assign)
                elif isinstance(stmt, ast.Expr) and _is_memory_allocation_expr(stmt.value):
                    lineno = getattr(stmt, "lineno", loop_info.line_number)
                    candidates.append(
                        Candidate.create(
                            rule_id=self.RULE_ID,
                            confidence=RuleConfidence(0.76),
                            message="Excessive temporary allocation in loop.",
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
