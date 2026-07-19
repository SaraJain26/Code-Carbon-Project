# ADR-0001: Introduce a Minimal Analysis IR

## Status

Accepted.

## Context

Code-Carbon currently analyzes Python through Python's built-in AST. Future research work may need Java, JavaScript, C++, repository-level analysis, visualization, and ML-oriented feature extraction.

## Decision

Introduce `analysis.ir` with minimal language-independent primitives:

- `IRNodeKind`
- `IRLocation`
- `IRScope`
- `IRNode`
- `IRVisitor`

The current parser and visitors are not redesigned around the IR. `AnalysisResult` remains the public API.

## Trade-Offs

This creates an extension point without forcing premature migration. The cost is a small package that is not yet deeply integrated.

## Consequences

Future engines can gradually map Python AST output into IR nodes. Higher-level modules can be written against IR interfaces once the project supports multiple languages.
