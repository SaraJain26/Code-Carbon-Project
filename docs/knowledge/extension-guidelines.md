# EKB Extension Guidelines

Future researchers can add rules by editing YAML files.

## Adding a Rule

1. Choose a stable ID using the format `EKB-AREA-NNN`.
2. Select a category and severity from the documented enums.
3. Write a detector-neutral `detection` statement.
4. Provide a practical recommendation.
5. Add at least one reference.
6. Add relevant tags and language applicability.
7. Run the test suite.

## Keep Detection Out of the EKB

The EKB describes knowledge. It should not contain AST pattern matchers, complexity formulas, carbon estimates, or executable optimization logic.

## Versioning

Increment rule versions when descriptions, rationale, detection semantics, or recommendation text materially change.

## Research Experimentation

Experimental rule files can be loaded with `RuleLoader.load_files([...])` and composed into a `RuleRepository`. This allows alternative rule sets without changing package code.
