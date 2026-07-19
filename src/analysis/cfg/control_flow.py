"""Lightweight control flow graph for Python functions and modules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CFGNode:
    """A lightweight control-flow node.

    Future CFG work can specialize nodes into explicit entry/exit, branch,
    exception, and loop-back categories while preserving this base shape.
    """

    id: int
    label: str
    node_type: str
    line_number: int | None
    scope: str


@dataclass(frozen=True)
class CFGEdge:
    """A directed control-flow edge.

    The `label` field is the extension point for branch labels, exceptional
    edges, loop back edges, and path traversal annotations.
    """

    source: int
    target: int
    label: str = "next"


class ControlFlowGraph:
    """Mutable lightweight control-flow graph.

    This class intentionally avoids advanced algorithms. Its node and edge
    storage is stable enough for later dominator analysis, path traversal, and
    graph export modules to be added alongside it.
    """

    def __init__(self) -> None:
        self.nodes: list[CFGNode] = []
        self.edges: list[CFGEdge] = []
        self._nodes_by_id: dict[int, CFGNode] = {}
        self._successors: dict[int, set[int]] = {}
        self._next_id = 1

    def add_node(self, label: str, node_type: str, line_number: int | None, scope: str) -> int:
        node_id = self._next_id
        self._next_id += 1
        node = CFGNode(node_id, label, node_type, line_number, scope)
        self.nodes.append(node)
        self._nodes_by_id[node_id] = node
        return node_id

    def add_edge(self, source: int, target: int, label: str = "next") -> None:
        self.edges.append(CFGEdge(source, target, label))
        self._successors.setdefault(source, set()).add(target)

    def successors(self, node_id: int) -> list[CFGNode]:
        return [self._nodes_by_id[target] for target in sorted(self._successors.get(node_id, set()))]
