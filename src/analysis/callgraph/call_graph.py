"""Directed call graph representation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class CallGraphEdge:
    """A directed caller-to-callee edge."""

    caller: str
    callee: str
    line_number: int
    is_recursive: bool = False


class CallGraph:
    """Directed graph with recursion helpers.

    The current public API is intentionally small. Internally the graph keeps
    forward and reverse adjacency indexes so future research passes can add
    strongly connected components, transitive dependencies, graph metrics,
    fan-in/fan-out, and export adapters without changing callers.
    """

    def __init__(self) -> None:
        self.nodes: set[str] = set()
        self.edges: list[CallGraphEdge] = []
        self._forward: dict[str, set[str]] = defaultdict(set)
        self._reverse: dict[str, set[str]] = defaultdict(set)

    def add_edge(self, caller: str, callee: str, line_number: int) -> None:
        self.nodes.update({caller, callee})
        edge = CallGraphEdge(
            caller=caller,
            callee=callee,
            line_number=line_number,
            is_recursive=self._is_direct_recursion(caller, callee),
        )
        self.edges.append(edge)
        self._forward[caller].add(callee)
        self._reverse[callee].add(caller)

    def callees(self, caller: str) -> set[str]:
        return set(self._forward.get(caller, set()))

    def callers(self, callee: str) -> set[str]:
        return set(self._reverse.get(callee, set()))

    def recursive_functions(self) -> set[str]:
        return {edge.caller for edge in self.edges if edge.is_recursive}

    def mutual_recursions(self) -> set[tuple[str, str]]:
        pairs: set[tuple[str, str]] = set()
        for caller, callee in self._edge_pairs():
            if caller != callee and caller in self._forward.get(callee, set()):
                pairs.add(tuple(sorted((caller, callee))))
        return pairs

    def traverse_from(self, start: str) -> list[str]:
        visited: set[str] = set()
        ordered: list[str] = []

        def visit(node: str) -> None:
            if node in visited:
                return
            visited.add(node)
            ordered.append(node)
            for callee in sorted(self.callees(node)):
                visit(callee)

        visit(start)
        return ordered

    def _edge_pairs(self) -> Iterable[tuple[str, str]]:
        for caller, callees in self._forward.items():
            for callee in callees:
                yield caller, callee

    def _is_direct_recursion(self, caller: str, callee: str) -> bool:
        return caller.split(".")[-1] == callee.split(".")[-1]
