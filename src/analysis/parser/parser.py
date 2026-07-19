"""Static analysis engine orchestration."""

from __future__ import annotations

import ast
from pathlib import Path

from analysis.callgraph import CallGraph
from analysis.models import AnalysisResult, CallInfo, ModuleInfo
from analysis.visitors.async_visitor import AsyncVisitor
from analysis.visitors.call_visitor import CallVisitor
from analysis.visitors.cfg_visitor import CFGVisitor
from analysis.visitors.class_visitor import ClassVisitor
from analysis.visitors.exception_visitor import ExceptionVisitor
from analysis.visitors.function_visitor import FunctionVisitor
from analysis.visitors.import_visitor import ImportVisitor
from analysis.visitors.loop_visitor import LoopVisitor
from analysis.visitors.metadata_visitor import MetadataVisitor
from analysis.visitors.symbol_visitor import SymbolVisitor


class StaticAnalysisEngine:
    """Coordinates focused static analysis passes over Python source code."""

    def analyze_file(self, source_file: str | Path) -> AnalysisResult:
        path = Path(source_file)
        source = path.read_text(encoding="utf-8")
        return self.analyze_source(source, path)

    def analyze_source(self, source: str, source_file: str | Path = "<memory>") -> AnalysisResult:
        path = Path(source_file)
        tree = ast.parse(source, filename=str(path), type_comments=True)
        module = ModuleInfo(
            source_file=path,
            name=path.stem,
            docstring=ast.get_docstring(tree),
            line_count=len(source.splitlines()),
        )

        function_visitor = FunctionVisitor()
        class_visitor = ClassVisitor()
        import_visitor = ImportVisitor(path)
        loop_visitor = LoopVisitor()
        async_visitor = AsyncVisitor()
        exception_visitor = ExceptionVisitor()
        symbol_visitor = SymbolVisitor()
        metadata_visitor = MetadataVisitor(path)
        cfg_visitor = CFGVisitor()

        for visitor in (
            function_visitor,
            class_visitor,
            import_visitor,
            loop_visitor,
            async_visitor,
            exception_visitor,
            symbol_visitor,
            metadata_visitor,
            cfg_visitor,
        ):
            visitor.visit(tree)

        user_names = {function.name for function in function_visitor.functions}
        user_names.update(cls.name for cls in class_visitor.classes)
        call_visitor = CallVisitor(user_names)
        call_visitor.visit(tree)

        call_graph = self._build_call_graph(call_visitor.calls)
        recursive_names = call_graph.recursive_functions()
        for function in function_visitor.functions:
            if function.qualified_name in recursive_names or function.name in recursive_names:
                function.is_recursive = True

        return AnalysisResult(
            module=module,
            functions=function_visitor.functions,
            classes=class_visitor.classes,
            loops=loop_visitor.loops,
            calls=call_visitor.calls,
            imports=import_visitor.imports,
            file_operations=call_visitor.file_operations,
            network_operations=call_visitor.network_operations,
            async_operations=async_visitor.async_operations,
            exceptions=exception_visitor.exceptions,
            call_graph=call_graph,
            control_flow_graph=cfg_visitor.graph,
            symbol_table=symbol_visitor.symbol_table,
            metadata=metadata_visitor.registry,
        )

    def _build_call_graph(self, calls: list[CallInfo]) -> CallGraph:
        graph = CallGraph()
        for call in calls:
            graph.add_edge(call.caller, call.callee, call.line_number)
        return graph
