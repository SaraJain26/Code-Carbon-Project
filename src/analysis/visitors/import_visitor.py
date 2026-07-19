"""Import extraction and classification."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from analysis.models import ImportInfo, ImportType


class ImportVisitor(ast.NodeVisitor):
    """Extracts standard-library, third-party, and local imports."""

    def __init__(self, source_file: Path) -> None:
        self.source_file = source_file
        self.imports: list[ImportInfo] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = alias.name.split(".")[0]
            self.imports.append(
                ImportInfo(
                    module=alias.name,
                    name=None,
                    alias=alias.asname,
                    line_number=node.lineno,
                    import_type=self._classify(root, 0),
                )
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        root = module.split(".")[0]
        for alias in node.names:
            self.imports.append(
                ImportInfo(
                    module=module,
                    name=alias.name,
                    alias=alias.asname,
                    line_number=node.lineno,
                    import_type=self._classify(root, node.level),
                    is_from_import=True,
                    level=node.level,
                )
            )

    def _classify(self, root: str, level: int) -> ImportType:
        if level > 0:
            return ImportType.LOCAL
        if root in sys.stdlib_module_names:
            return ImportType.STANDARD_LIBRARY
        if (self.source_file.parent / f"{root}.py").exists() or (self.source_file.parent / root).exists():
            return ImportType.LOCAL
        return ImportType.THIRD_PARTY
