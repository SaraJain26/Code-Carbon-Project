import ast
from detector.context import DetectionContext
from detector.models import (
    Candidate,
    CandidateEvidence,
    EvidenceKind,
)
from knowledge import RuleConfidence


class MemoryAllocationDetector:
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
                if isinstance(stmt, ast.Assign):
                    if isinstance(stmt.value, (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp)):
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
