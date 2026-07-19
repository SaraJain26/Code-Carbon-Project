# Static Analysis Engine API

## Entry Point

```python
from analysis import StaticAnalysisEngine

engine = StaticAnalysisEngine()
result = engine.analyze_file("examples/benchmarks/nested_loops.py")
```

Use `analyze_source(source, source_file="<memory>")` for in-memory analysis.

## Result Model

`AnalysisResult` contains:

- `module`: module-level file metadata.
- `functions`: `FunctionInfo` entries with parameters, decorators, recursion, return annotations, docstrings, locals, statement count, and line count.
- `classes`: `ClassInfo` entries with inheritance, methods, decorators, class variables, and docstrings.
- `loops`: `LoopInfo` entries with loop type, line range, nesting depth, parent class/function, and structural flags.
- `calls`: `CallInfo` entries with caller, callee, line number, and call type.
- `imports`: `ImportInfo` entries classified as standard-library, third-party, or local.
- `file_operations`: detected file-system operations.
- `network_operations`: detected API/network operations.
- `async_operations`: async function, await, async for, and async with usage.
- `exceptions`: try, except, finally, raise, and custom exception usage.
- `call_graph`: directed graph with recursion helpers.
- `control_flow_graph`: lightweight CFG over functions and control constructs.
- `symbol_table`: scope-aware definitions, assignments, and references.
- `metadata`: per-AST-node location, scope, parent, depth, and node type.

## Extension Points

Each visitor has a single responsibility and can be replaced or extended without changing the parser interface:

- `FunctionVisitor`
- `ClassVisitor`
- `LoopVisitor`
- `CallVisitor`
- `ImportVisitor`
- `AsyncVisitor`
- `ExceptionVisitor`
- `SymbolVisitor`
- `MetadataVisitor`
- `CFGVisitor`
