# AnalysisResult API

`AnalysisResult` is the stable public output of the static analysis engine.

## Fields

- `module: ModuleInfo`
- `functions: list[FunctionInfo]`
- `classes: list[ClassInfo]`
- `loops: list[LoopInfo]`
- `calls: list[CallInfo]`
- `imports: list[ImportInfo]`
- `file_operations: list[FileOperationInfo]`
- `network_operations: list[NetworkOperationInfo]`
- `async_operations: list[AsyncInfo]`
- `exceptions: list[ExceptionInfo]`
- `call_graph: CallGraph | None`
- `control_flow_graph: ControlFlowGraph | None`
- `symbol_table: SymbolTable | None`
- `metadata: MetadataRegistry | None`

The public shape is backward compatible with Phase 2. The Phase 2.5 refinement strengthened the final four fields from generic `object` references to concrete type hints.
