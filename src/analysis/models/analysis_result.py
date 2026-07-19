"""Dataclasses representing static analysis output."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from analysis.callgraph import CallGraph
    from analysis.cfg import ControlFlowGraph
    from analysis.metadata import MetadataRegistry
    from analysis.symbols import SymbolTable


class LoopType(str, Enum):
    """Supported Python loop constructs."""

    FOR = "for"
    WHILE = "while"
    ASYNC_FOR = "async_for"


class CallType(str, Enum):
    """Classification for a function call."""

    BUILTIN = "builtin"
    LIBRARY = "library"
    USER_DEFINED = "user_defined"
    METHOD = "method"
    UNKNOWN = "unknown"


class ImportType(str, Enum):
    """Classification for imports."""

    STANDARD_LIBRARY = "standard_library"
    THIRD_PARTY = "third_party"
    LOCAL = "local"


@dataclass(frozen=True)
class ParameterInfo:
    """Function parameter metadata."""

    name: str
    annotation: str | None = None
    default: str | None = None
    kind: str = "positional_or_keyword"


@dataclass(frozen=True)
class ModuleInfo:
    """Top-level source module metadata."""

    source_file: Path
    name: str
    docstring: str | None
    line_count: int


@dataclass
class FunctionInfo:
    """Structural data extracted from a Python function."""

    name: str
    qualified_name: str
    line_number: int
    end_line: int
    parameters: list[ParameterInfo] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    is_async: bool = False
    is_recursive: bool = False
    return_annotation: str | None = None
    docstring: str | None = None
    local_variables: set[str] = field(default_factory=set)
    statement_count: int = 0
    line_count: int = 0
    parent_class: str | None = None


@dataclass
class ClassInfo:
    """Structural data extracted from a Python class."""

    name: str
    qualified_name: str
    line_number: int
    end_line: int
    bases: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    class_variables: set[str] = field(default_factory=set)
    docstring: str | None = None


@dataclass
class LoopInfo:
    """Structural data extracted from a loop."""

    loop_type: LoopType
    line_number: int
    end_line: int
    nesting_depth: int
    parent_function: str | None = None
    parent_class: str | None = None
    contains_api_call: bool = False
    contains_file_io: bool = False
    contains_recursion: bool = False
    contains_async_operations: bool = False


@dataclass(frozen=True)
class CallInfo:
    """A call expression and its context."""

    caller: str
    callee: str
    line_number: int
    call_type: CallType


@dataclass(frozen=True)
class ImportInfo:
    """An import statement with package classification."""

    module: str
    name: str | None
    alias: str | None
    line_number: int
    import_type: ImportType
    is_from_import: bool = False
    level: int = 0


@dataclass(frozen=True)
class FileOperationInfo:
    """A detected file-system operation."""

    operation: str
    line_number: int
    caller: str
    target: str | None = None


@dataclass(frozen=True)
class NetworkOperationInfo:
    """A detected network or API operation."""

    operation: str
    line_number: int
    caller: str
    library: str | None = None


@dataclass(frozen=True)
class AsyncInfo:
    """Async syntax usage."""

    operation: str
    line_number: int
    scope: str


@dataclass(frozen=True)
class ExceptionInfo:
    """Exception-related syntax usage."""

    operation: str
    line_number: int
    scope: str
    exception_type: str | None = None


@dataclass
class AnalysisResult:
    """Unified result produced by the static analysis engine."""

    module: ModuleInfo
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    loops: list[LoopInfo] = field(default_factory=list)
    calls: list[CallInfo] = field(default_factory=list)
    imports: list[ImportInfo] = field(default_factory=list)
    file_operations: list[FileOperationInfo] = field(default_factory=list)
    network_operations: list[NetworkOperationInfo] = field(default_factory=list)
    async_operations: list[AsyncInfo] = field(default_factory=list)
    exceptions: list[ExceptionInfo] = field(default_factory=list)
    call_graph: CallGraph | None = None
    control_flow_graph: ControlFlowGraph | None = None
    symbol_table: SymbolTable | None = None
    metadata: MetadataRegistry | None = None
