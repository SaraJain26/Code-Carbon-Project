# Parser Workflow

`StaticAnalysisEngine` is the public entry point.

1. Read source from file or memory.
2. Parse Python source using the standard `ast` module.
3. Build `ModuleInfo`.
4. Run focused extraction visitors:
   - functions
   - classes
   - imports
   - loops
   - async constructs
   - exceptions
   - symbols
   - metadata
   - lightweight CFG
5. Run call extraction after user-defined symbols are known.
6. Build the directed call graph.
7. Mark direct recursion based on graph output.
8. Return one `AnalysisResult`.

The parser does not perform carbon estimation, complexity scoring, energy smell scoring, or scheduling.
