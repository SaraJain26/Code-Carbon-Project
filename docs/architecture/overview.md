# Static Analysis Architecture Overview

The Code-Carbon static analysis engine is the structural foundation for later research modules. It parses Python source code and returns a typed `AnalysisResult` without estimating energy, carbon, or optimization impact.

## Dependency Direction

```text
parser -> visitors -> models
parser -> callgraph / cfg / symbols / metadata
visitors -> parser helper utilities
visitors -> shared utilities
models -> type-only graph/table/registry references
```

The parser coordinates passes. Visitors extract one kind of information. Models describe output. Graph, symbol, metadata, and IR packages provide reusable structures.

## Major Components

- `analysis.parser`: entry point and AST orchestration.
- `analysis.visitors`: focused extraction passes.
- `analysis.models`: public dataclass result model.
- `analysis.callgraph`: directed call graph and recursion helpers.
- `analysis.cfg`: lightweight control-flow graph.
- `analysis.symbols`: scope-aware symbol table.
- `analysis.metadata`: AST node metadata registry.
- `analysis.utils`: reusable syntactic inspection helpers.
- `analysis.ir`: initial language-independent internal representation.

## Extension Rule

Future energy smell, complexity, and carbon modules should consume `AnalysisResult` or the evolving IR. They should not add heuristics into visitors.
