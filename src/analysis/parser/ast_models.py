"""Utilities for rendering AST model fragments."""

from __future__ import annotations

import ast


def unparse(node: ast.AST | None) -> str | None:
    """Return readable source for an AST node when available."""

    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return node.__class__.__name__


def call_name(node: ast.AST) -> str:
    """Return a dotted call or attribute name."""

    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        return call_name(node.func)
    if isinstance(node, ast.Subscript):
        return call_name(node.value)
    return ""


def assigned_names(node: ast.AST) -> set[str]:
    """Collect variable names assigned by a target AST node."""

    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
    return names
