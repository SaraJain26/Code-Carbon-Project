# Implementation Report: Phase 2.5 Static Analysis Engine Architecture Refinement

## 1. Objective

Strengthen the Code-Carbon Static Analysis Engine architecture before implementing higher-level research modules such as Energy Smell Detection, Complexity Scoring, Carbon Prediction, and Scheduling.

This session preserved public behavior while improving type safety, modularity, documentation, repository organization, and future extensibility.

## 2. Executive Summary

The refinement introduced a minimal language-independent IR package, replaced generic `object` result references with concrete type hints, centralized reusable call/file/network classification, improved graph internals for future algorithms, documented visitor and parser workflows, and created repository areas for research, datasets, and benchmark harnesses.

No carbon estimation, complexity scoring, optimization recommendation, or smell detection logic was added.

All existing tests pass.

## 3. Repository Tree

Key tree after refinement:

```text
.
├── .gitignore
├── README.md
├── benchmarks/README.md
├── datasets/README.md
├── docs/
│   ├── api.md
│   ├── api/analysis-result.md
│   ├── architecture/
│   │   ├── overview.md
│   │   ├── parser-workflow.md
│   │   └── visitor-workflow.md
│   ├── decisions/
│   │   ├── ADR-0001-analysis-ir.md
│   │   └── ADR-0002-visitor-responsibilities.md
│   └── reports/IMPLEMENTATION_REPORT_PHASE_2_SESSION_2.md
├── examples/benchmarks/
├── pyproject.toml
├── research/
│   ├── README.md
│   ├── evaluation/README.md
│   └── experiments/README.md
├── src/analysis/
│   ├── callgraph/
│   ├── cfg/
│   ├── ir/
│   ├── metadata/
│   ├── models/
│   ├── parser/
│   ├── symbols/
│   ├── utils/
│   └── visitors/
└── tests/
```

## 4. Files Created

- `.gitignore`
- `src/analysis/ir/__init__.py`
- `src/analysis/ir/nodes.py`
- `src/analysis/utils/__init__.py`
- `src/analysis/utils/calls.py`
- `docs/architecture/overview.md`
- `docs/architecture/parser-workflow.md`
- `docs/architecture/visitor-workflow.md`
- `docs/api/analysis-result.md`
- `docs/decisions/ADR-0001-analysis-ir.md`
- `docs/decisions/ADR-0002-visitor-responsibilities.md`
- `docs/reports/IMPLEMENTATION_REPORT_PHASE_2_SESSION_2.md`
- `research/README.md`
- `research/experiments/README.md`
- `research/evaluation/README.md`
- `datasets/README.md`
- `benchmarks/README.md`

## 5. Files Modified

- `src/analysis/models/analysis_result.py`
- `src/analysis/visitors/call_visitor.py`
- `src/analysis/visitors/loop_visitor.py`
- `src/analysis/callgraph/call_graph.py`
- `src/analysis/cfg/control_flow.py`
- `src/analysis/parser/parser.py`

## 6. Architecture Decisions

### Stronger Typed Result References

`AnalysisResult` previously exposed `call_graph`, `control_flow_graph`, `symbol_table`, and `metadata` as `object | None`. These are now typed as concrete interfaces using `TYPE_CHECKING` imports.

Trade-off: runtime imports remain avoided, reducing circular import risk. Static tooling and contributors now see the actual expected types.

### Minimal Analysis IR

An `analysis.ir` package was introduced with `IRNodeKind`, `IRLocation`, `IRScope`, `IRNode`, and `IRVisitor`.

Trade-off: the current Python parser was not redesigned around the IR. This avoids a premature migration while creating a stable target for future language-independent analysis.

### Centralized Call Classification

Call, file-operation, network-operation, and async syntax helpers were moved into `analysis.utils.calls`.

Trade-off: visitors now depend on a shared utility. This is preferable to duplicating syntactic classification rules across visitors.

### Graph Extension Readiness

`CallGraph` now maintains forward and reverse adjacency indexes while preserving `nodes`, `edges`, `callees`, `callers`, `recursive_functions`, `mutual_recursions`, and `traverse_from`.

Trade-off: internal storage is slightly larger, but future algorithms can be added without redesign.

### CFG Extension Readiness

`ControlFlowGraph` now stores node lookup and successor indexes. Node and edge docstrings describe extension points for entry/exit nodes, branch labels, loop back edges, dominator analysis, and path traversal.

Trade-off: the CFG remains lightweight and does not attempt advanced correctness guarantees yet.

## 7. Public APIs

- `StaticAnalysisEngine.analyze_file(source_file: str | Path) -> AnalysisResult`
- `StaticAnalysisEngine.analyze_source(source: str, source_file: str | Path = "<memory>") -> AnalysisResult`
- `AnalysisResult`
- `ModuleInfo`
- `FunctionInfo`
- `ClassInfo`
- `LoopInfo`
- `CallInfo`
- `ImportInfo`
- `FileOperationInfo`
- `NetworkOperationInfo`
- `AsyncInfo`
- `ExceptionInfo`
- `CallGraph`
- `ControlFlowGraph`
- `SymbolTable`
- `MetadataRegistry`
- `IRNode`, `IRNodeKind`, `IRLocation`, `IRScope`, `IRVisitor`

No public API names were removed.

## 8. Data Models

Modified:

- `AnalysisResult`: final infrastructure fields now use concrete type hints.

Introduced:

- `CallInspection`: normalized call-name view with full, root, and leaf names.
- `IRNodeKind`: language-neutral node categories.
- `IRLocation`: portable source location model.
- `IRScope`: portable lexical scope model.
- `IRNode`: minimal language-independent analysis node.

Existing dataclass models remain compatible.

## 9. Dependencies

No external runtime dependencies were added.

New standard-library usage:

- `typing.TYPE_CHECKING`
- `typing.Protocol`
- `collections.defaultdict`
- `collections.abc.Iterable`

No dependencies were removed.

## 10. Testing

Executed:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p 'test_*.py' -v
```

Result:

```text
Ran 5 tests in 0.047s
OK
```

Regression found and fixed:

- `LoopVisitor` still referenced the old direct `call_name` helper after classification centralization.
- Fixed by using `CallInspection.from_call(child).leaf_name`.

No test expectations were changed.

## 11. Example Usage

Existing usage remains unchanged:

```python
from analysis import StaticAnalysisEngine

engine = StaticAnalysisEngine()
result = engine.analyze_file("examples/benchmarks/nested_loops.py")

print(result.functions)
print(result.call_graph.recursive_functions())
```

The IR package is available for future consumers:

```python
from analysis.ir import IRNode, IRNodeKind, IRLocation, IRScope
```

The current parser does not yet emit a full IR tree.

## 12. Future Integration

Energy Smell Detection:

- Can consume `AnalysisResult.loops`, `calls`, `file_operations`, `network_operations`, and `async_operations`.
- Should not be placed inside visitors.

Complexity Engine:

- Can consume functions, loops, CFG, and symbol table.
- Can later consume IR nodes for language-independent complexity features.

Carbon Predictor:

- Can consume higher-level features produced by smell and complexity engines.
- The static analysis engine intentionally does not estimate carbon.

Hardware Profiler:

- Remains independent from source analysis.
- Can be composed with analysis output by a future estimator.

Dashboard:

- Can visualize typed result objects, call graph edges, CFG nodes, and metadata.

## 13. Technical Debt

- The current parser is Python-only.
- The IR package is introduced but not yet populated by the parser.
- CFG is lightweight and approximate.
- Call classification is syntactic and import-alias awareness is limited.
- Symbol resolution is lexical but not a full Python name-binding implementation.
- Generated `__pycache__` files may exist locally after tests; `.gitignore` now prevents them from being committed.

## 14. Deferred Architecture Improvements

- Full AST-to-IR lowering pass: deferred to avoid redesigning working Python analysis before multi-language requirements are concrete.
- Strongly connected component detection: deferred because the prompt requested preparation, not implementation.
- Full dominator/tree/path algorithms for CFG: deferred because the current requirement is lightweight CFG evolution readiness.
- Import alias-aware call classification: deferred because it changes semantic precision and needs dedicated tests.
- Repository-level multi-file symbol resolution: deferred for a later repository analysis phase.

## 15. Review Checklist

- Architecture: completed.
- Documentation: completed.
- Typing: improved.
- Maintainability: improved through shared call utilities and typed result links.
- Extensibility: improved through IR, graph indexes, CFG indexes, docs, and repository organization.
- Backward compatibility: preserved.
- Tests: passing.

## 16. Self Evaluation

Strengths:

- Refinement stayed focused and did not mix future research logic into extraction.
- Type safety improved without runtime circular imports.
- The IR package creates a clean future path for multi-language analysis.
- Existing tests passed without changing assertions.

Weaknesses:

- IR is intentionally minimal and not yet operationally integrated.
- CFG and symbol analysis remain lightweight approximations.
- Call classification still relies on syntactic names rather than import-aware resolution.

Future work:

- Add an IR lowering adapter.
- Add richer graph algorithms as separate modules.
- Add repository-level analysis and alias-aware call resolution.

## 17. Architecture Review

### Parser

Current maturity: solid for single-file Python analysis.

Strengths: simple orchestration, stable entry point, no scoring logic.

Weaknesses: Python-only, sequential visitor execution, no repository-level context.

Extension points: parser frontend interface, IR lowering, repository parser.

### Visitors

Current maturity: strong extractor pattern.

Strengths: one visitor per responsibility.

Weaknesses: some extraction fields still encode broad structural signals such as loop-contained file/network calls.

Extension points: add visitors for comprehensions, decorators, typing, imports, or dataflow without merging responsibilities.

### AnalysisResult

Current maturity: stable public API.

Strengths: unified typed output.

Weaknesses: not yet versioned.

Extension points: add optional fields while preserving existing fields.

### Call Graph

Current maturity: useful directed graph for calls and recursion.

Strengths: adjacency indexes now support future algorithms.

Weaknesses: syntactic calls only.

Extension points: SCCs, transitive dependencies, fan-in/fan-out, exports, cycle reports.

### CFG

Current maturity: lightweight structural CFG.

Strengths: indexed nodes and successor lookup.

Weaknesses: approximate flow, limited exception semantics.

Extension points: entry/exit nodes, branch labeling, loop back edges, dominator analysis, path traversal.

### Symbol Table

Current maturity: useful lexical table.

Strengths: scopes, symbols, assignments, references.

Weaknesses: not full Python binding semantics.

Extension points: imports, aliases, closures, comprehensions, global/nonlocal.

### Metadata

Current maturity: solid AST-node registry.

Strengths: parent, scope, depth, location, node type.

Weaknesses: keyed by AST object identity, which is frontend-specific.

Extension points: IR metadata mapping, stable node identifiers.

### Analysis IR

Current maturity: initial scaffold.

Strengths: language-neutral contracts without forcing migration.

Weaknesses: no lowering pipeline yet.

Extension points: frontend adapters, IR visitors, language-independent feature extraction.

## 18. Unimplemented Requirements

Completed requirements:

- Strengthened `AnalysisResult` typing.
- Added `analysis.ir`.
- Preserved existing APIs.
- Kept visitors as extractors.
- Centralized duplicated call/file/network classification.
- Improved CallGraph internals.
- Improved CFG internals and documentation.
- Added architecture, API, decisions, and report documentation.
- Added research, datasets, and benchmark placeholder directories.
- Ran existing tests.

Partially completed requirements:

- Public API review: completed for existing public classes touched in this session; deeper docstring expansion for every single existing dataclass can continue incrementally.
- Coupling review: reduced duplicated call logic and avoided circular imports; no automated import graph tooling was added.

Intentionally skipped requirements:

- Advanced graph algorithms: skipped because the prompt requested preparation only.
- Advanced CFG algorithms: skipped because the prompt requested lightweight CFG preservation.
- Full multi-language support: skipped because Phase 2.5 only requested preparation for language independence.
- IR migration: skipped to preserve behavior and avoid a major redesign.

Completion checklist:

- All tests pass: yes.
- Existing APIs remain compatible: yes.
- Existing functionality unchanged: yes.
- Documentation updated: yes.
- No regressions introduced: yes, after fixing the transient loop utility reference.
- Implementation report generated: yes.
- Deferred work documented: yes.
