"""Metadata registry construction visitor."""

from __future__ import annotations

import ast
from pathlib import Path

from analysis.metadata import MetadataRegistry, NodeMetadata
from analysis.parser.visitors import ContextualVisitor


class MetadataVisitor(ContextualVisitor):
    """Records source location, parent, scope, depth, and AST type for every node."""

    def __init__(self, source_file: Path) -> None:
        super().__init__()
        self.source_file = source_file
        self.registry = MetadataRegistry()
        self._parent_stack: list[ast.AST] = []
        self._depth = 0

    def visit(self, node: ast.AST) -> None:
        parent = self._parent_stack[-1] if self._parent_stack else None
        self.registry.add(
            node,
            NodeMetadata(
                node_id=id(node),
                source_file=self.source_file,
                start_line=getattr(node, "lineno", None),
                end_line=getattr(node, "end_lineno", None),
                parent_id=id(parent) if parent else None,
                scope=self.context.scope,
                depth=self._depth,
                node_type=node.__class__.__name__,
            ),
        )
        self._parent_stack.append(node)
        self._depth += 1
        super().visit(node)
        self._depth -= 1
        self._parent_stack.pop()
