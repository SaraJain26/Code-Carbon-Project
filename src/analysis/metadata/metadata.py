"""AST node metadata registry."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NodeMetadata:
    """Location, scope, and hierarchy metadata for one AST node."""

    node_id: int
    source_file: Path
    start_line: int | None
    end_line: int | None
    parent_id: int | None
    scope: str
    depth: int
    node_type: str


class MetadataRegistry:
    """Stores metadata for AST nodes by object identity."""

    def __init__(self) -> None:
        self._items: dict[int, NodeMetadata] = {}

    def add(self, node: ast.AST, metadata: NodeMetadata) -> None:
        self._items[id(node)] = metadata

    def get(self, node: ast.AST) -> NodeMetadata | None:
        return self._items.get(id(node))

    def all(self) -> list[NodeMetadata]:
        return list(self._items.values())

    def __len__(self) -> int:
        return len(self._items)
