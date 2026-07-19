"""Reusable call inspection and classification utilities.

This module intentionally performs only syntactic classification. It does not
score energy usage, estimate complexity, or apply optimization heuristics.
"""

from __future__ import annotations

import ast
import builtins
from dataclasses import dataclass

from analysis.models import CallType
from analysis.parser.ast_models import call_name

FILE_METHODS: frozenset[str] = frozenset(
    {"open", "read", "write", "append", "seek", "close", "read_text", "write_text", "read_bytes", "write_bytes"}
)
OS_FILE_OPERATIONS: frozenset[str] = frozenset(
    {"os.remove", "os.rename", "os.replace", "os.mkdir", "os.makedirs", "os.rmdir", "os.path.exists"}
)
NETWORK_ROOTS: frozenset[str] = frozenset({"requests", "urllib", "httpx", "aiohttp", "socket", "websocket", "grpc"})
HTTP_METHODS: frozenset[str] = frozenset({"get", "post", "put", "patch", "delete", "head", "options", "request"})


@dataclass(frozen=True)
class CallInspection:
    """Normalized view of a call expression."""

    full_name: str
    root_name: str
    leaf_name: str

    @classmethod
    def from_call(cls, node: ast.Call) -> "CallInspection":
        full_name = call_name(node.func)
        parts = full_name.split(".")
        return cls(full_name=full_name, root_name=parts[0] if parts else "", leaf_name=parts[-1] if parts else "")


class CallClassifier:
    """Classifies calls without depending on any visitor implementation."""

    def __init__(self, user_defined_names: set[str] | None = None) -> None:
        self.user_defined_names = user_defined_names or set()
        self._builtin_names = frozenset(dir(builtins))

    def classify(self, inspection: CallInspection) -> CallType:
        if inspection.full_name in self.user_defined_names or inspection.leaf_name in self.user_defined_names:
            return CallType.USER_DEFINED
        if inspection.root_name in self._builtin_names:
            return CallType.BUILTIN
        if inspection.root_name in NETWORK_ROOTS:
            return CallType.LIBRARY
        if "." in inspection.full_name:
            return CallType.METHOD
        return CallType.UNKNOWN

    def is_file_operation(self, inspection: CallInspection) -> bool:
        return (
            inspection.leaf_name in FILE_METHODS
            or inspection.full_name.startswith("pathlib.")
            or inspection.full_name in OS_FILE_OPERATIONS
        )

    def is_network_operation(self, inspection: CallInspection) -> bool:
        return inspection.root_name in NETWORK_ROOTS or inspection.leaf_name in HTTP_METHODS

    def network_library(self, inspection: CallInspection) -> str | None:
        return inspection.root_name if inspection.root_name in NETWORK_ROOTS else None


def is_async_operation(node: ast.AST) -> bool:
    """Return whether a node contains async syntax."""

    return any(isinstance(child, (ast.Await, ast.AsyncWith, ast.AsyncFor)) for child in ast.walk(node))
