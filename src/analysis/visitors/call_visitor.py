"""Call, file-operation, and network-operation extraction."""

from __future__ import annotations

import ast

from analysis.models import CallInfo, CallType, FileOperationInfo, NetworkOperationInfo
from analysis.parser.visitors import ContextualVisitor
from analysis.utils import CallClassifier, CallInspection


class CallVisitor(ContextualVisitor):
    """Extracts calls and classifies common file/network operations."""

    def __init__(self, user_defined_names: set[str]) -> None:
        super().__init__()
        self.user_defined_names = user_defined_names
        self.classifier = CallClassifier(user_defined_names)
        self.calls: list[CallInfo] = []
        self.file_operations: list[FileOperationInfo] = []
        self.network_operations: list[NetworkOperationInfo] = []

    def visit_Call(self, node: ast.Call) -> None:
        inspection = CallInspection.from_call(node)
        callee = inspection.full_name
        caller = self.context.parent_function or self.context.scope
        self.calls.append(CallInfo(caller=caller, callee=callee, line_number=node.lineno, call_type=self._call_type(inspection)))
        self._record_file_operation(inspection, node.lineno, caller)
        self._record_network_operation(inspection, node.lineno, caller)
        self.generic_visit(node)

    def _call_type(self, inspection: CallInspection) -> CallType:
        return self.classifier.classify(inspection)

    def _record_file_operation(self, inspection: CallInspection, line_number: int, caller: str) -> None:
        if self.classifier.is_file_operation(inspection):
            self.file_operations.append(FileOperationInfo(operation=inspection.full_name, line_number=line_number, caller=caller))

    def _record_network_operation(self, inspection: CallInspection, line_number: int, caller: str) -> None:
        if self.classifier.is_network_operation(inspection):
            self.network_operations.append(
                NetworkOperationInfo(
                    operation=inspection.full_name,
                    line_number=line_number,
                    caller=caller,
                    library=self.classifier.network_library(inspection),
                )
            )
