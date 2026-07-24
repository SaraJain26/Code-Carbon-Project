# Code-Carbon Static Analysis Engine

Code-Carbon is a publication-oriented research framework for **predictive carbon-aware software engineering**. The framework performs static analysis of Python source code and incrementally builds the foundation required for energy smell detection, software complexity assessment, and future predictive carbon estimation.

The project is being developed in modular stages. The current implementation includes the static analysis engine, energy knowledge base, detector framework, and complexity analysis module.

---

# Current Capabilities

## Static Analysis Engine

- Python AST parsing using the standard `ast` module.
- Function, async function, parameter, decorator, annotation, docstring, and local-variable extraction.
- Class, inheritance, method, decorator, and class-variable extraction.
- Loop detection with nesting depth and structural flags.
- Call extraction with builtin, library, user-defined, method, and unknown classification.
- Import extraction classified as standard library, third-party, or local.
- File operation detection for `open`, stream methods, `pathlib`, and common `os` operations.
- Network/API detection for `requests`, `urllib`, `httpx`, `aiohttp`, `socket`, `websocket`, `grpc`, and generic HTTP method calls.
- Async analysis for async functions, `await`, `async for`, and `async with`.
- Exception analysis for `try`, `except`, `finally`, `raise`, and custom exceptions.
- Scope-aware symbol table.
- Directed call graph with direct and mutual recursion helpers.
- Lightweight Control Flow Graph (CFG).
- AST metadata registry containing source location, parent, scope, depth, and node type.

---

## Energy Knowledge Base

The Energy Knowledge Base (EKB) stores detector-independent energy smell definitions as YAML-backed typed rules.

Features include:

- YAML rule loading
- Rule validation
- Duplicate detection
- Typed rule models
- Repository querying
- Extensible rule architecture

---

## Detector Framework

The detector framework provides a modular architecture for identifying energy-related software patterns.

Implemented components include:

- Detector registry
- Detector engine
- Detector context
- Rule evaluator
- Confidence scorer
- Finding generator
- Detector filtering

Current detectors include:

- Nested Loop Detector
- Recursive Computation Detector
- File Operation Detector
- Network Call Detector
- Async Operation Detector

---

## Complexity Analysis Module

The Complexity Analysis module measures structural software complexity and transforms raw metrics into normalized sustainability-oriented scores.

Implemented features:

- Cyclomatic Complexity extraction using **Radon**
- Maximum nesting depth
- Function density
- Energy smell integration
- Complexity normalization
- Structural Complexity Index (SCI)
- Carbon Impact Risk Score (CIRS)
- Risk classification
- Recommendation generation
- Complexity scoring engine

---

# Mathematical Model

The framework currently computes two composite metrics.

## Structural Complexity Index (SCI)

```
SCI =
0.50 × Cyclomatic Complexity
+ 0.30 × Maximum Nesting Depth
+ 0.20 × Function Density
```

---

## Carbon Impact Risk Score (CIRS)

```
CIRS =
0.55 × SCI
+ 0.45 × Energy Smell Score
```

---

## Risk Levels

| Score | Risk |
|--------|------|
| 0.00 – 0.20 | Very Low |
| 0.21 – 0.40 | Low |
| 0.41 – 0.60 | Moderate |
| 0.61 – 0.80 | High |
| 0.81 – 1.00 | Very High |

---

# Project Architecture

```
src/

├── analysis/
│   ├── parser/
│   ├── visitors/
│   ├── cfg/
│   ├── callgraph/
│   ├── metadata/
│   ├── models/
│   ├── symbols/
│   └── utils/
│
├── knowledge/
│   ├── rules/
│   ├── loader.py
│   ├── repository.py
│   ├── validation.py
│   └── models.py
│
├── detector/
│   ├── evaluators/
│   ├── extractors/
│   ├── generators/
│   ├── rules/
│   ├── scorers/
│   ├── configuration.py
│   ├── context.py
│   ├── engine.py
│   ├── interfaces.py
│   └── models.py
│
└── complexity/
    ├── metrics.py
    ├── radon_adapter.py
    ├── normalizer.py
    ├── scorer.py
    ├── engine.py
    └── models.py
```

---

# Quick Start

Install the project in editable mode.

```powershell
pip install -e .
```

Run the complete test suite.

```powershell
python -m unittest discover -s tests -v
```

---

# Example

```python
from analysis import StaticAnalysisEngine

engine = StaticAnalysisEngine()

result = engine.analyze_file(
    "examples/benchmarks/classes_exceptions.py"
)

print(result.functions)
print(result.call_graph.recursive_functions())
```

---

# Testing

The project currently contains comprehensive unit and integration tests covering:

- Static Analysis Engine
- Energy Knowledge Base
- Detector Framework
- Complexity Metrics
- Complexity Normalization
- Complexity Scoring
- Complexity Engine
- Radon Integration

Current status:

```
43 tests
43 passed
0 failures
```

---

# Documentation

API documentation:

```
docs/api.md
```

Knowledge base documentation:

```
docs/knowledge
```

---

# Current Development Status

Completed modules:

- ✅ Static Analysis Engine
- ✅ Energy Knowledge Base
- ✅ Detector Framework
- ✅ Complexity Analysis Module

Upcoming modules:

- Predictive Carbon Estimation
- Carbon-Aware Recommendation Engine
- Machine Learning Prediction Models
- Carbon Scheduling Framework
- Explainability & Reporting
- Research Evaluation Pipeline

---

# Research Objective

Code-Carbon aims to provide a modular framework for predictive carbon-aware software engineering by combining static program analysis, software complexity metrics, energy smell detection, and sustainability-oriented scoring. The long-term goal is to enable developers to estimate potential software energy impact early in the software development lifecycle, before deployment or execution.