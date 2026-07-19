# Code-Carbon Static Analysis Engine

Code-Carbon is a publication-oriented research framework for predictive carbon-aware software engineering. This repository currently implements the foundational static analysis engine. It does **not** estimate energy or carbon; it extracts reusable source-code structure for later modules such as energy smell detection, complexity scoring, carbon estimation, and scheduling.

## Capabilities

- Python AST parsing using the standard `ast` module.
- Function, async function, parameter, decorator, annotation, docstring, and local-variable extraction.
- Class, inheritance, method, decorator, and class-variable extraction.
- Loop detection with nesting depth and structural flags for API calls, file I/O, recursion, and async usage.
- Call extraction with builtin, library, user-defined, method, and unknown classification.
- Import extraction classified as standard library, third-party, or local.
- File operation detection for `open`, stream methods, `pathlib`, and common `os` operations.
- Network/API detection for `requests`, `urllib`, `httpx`, `aiohttp`, `socket`, `websocket`, `grpc`, and generic HTTP method calls.
- Async analysis for async functions, `await`, `async for`, and `async with`.
- Exception analysis for `try`, `except`, `finally`, `raise`, and custom exceptions.
- Scope-aware symbol table.
- Directed call graph with direct and mutual recursion helpers.
- Lightweight control-flow graph.
- AST metadata registry for source location, parent, scope, depth, and node type.
- Energy Knowledge Base for detector-independent energy rule metadata.

## Quick Start

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests -p "test_*.py" -v
```

```python
from analysis import StaticAnalysisEngine

engine = StaticAnalysisEngine()
result = engine.analyze_file("examples/benchmarks/classes_exceptions.py")

print(result.functions)
print(result.call_graph.recursive_functions())
```

## Architecture

```text
src/analysis/
  parser/
    parser.py          # StaticAnalysisEngine orchestration
    visitors.py        # shared contextual visitor base
    ast_models.py      # AST rendering helpers
  visitors/
    function_visitor.py
    loop_visitor.py
    call_visitor.py
    class_visitor.py
    import_visitor.py
    async_visitor.py
    exception_visitor.py
    symbol_visitor.py
    metadata_visitor.py
    cfg_visitor.py
  cfg/
    control_flow.py
  callgraph/
    call_graph.py
  symbols/
    symbol_table.py
  metadata/
    metadata.py
  models/
    analysis_result.py
```

## Examples

Benchmark programs live in `examples/benchmarks` and cover nested loops, recursion, async/network usage, file processing, classes, inheritance, and exceptions.

## API Documentation

See `docs/api.md`.

## Energy Knowledge Base

The EKB lives in `src/knowledge` and stores energy-smell knowledge as YAML-backed typed rules. It does not perform detection or carbon estimation.

```python
from knowledge import RuleLoader, RuleRepository

rules = RuleLoader().load_default_rules()
repository = RuleRepository(rules)
```

See `docs/knowledge`.
