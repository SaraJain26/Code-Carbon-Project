# EKB YAML Rule Schema

Rules are authored in YAML so researchers can add or adjust knowledge without editing Python code.

## Document Shape

```yaml
schema_version: "1.0"
rules:
  - id: EKB-COMP-001
    name: Excessive nested loops
    description: Deeply nested iteration can multiply work.
    category: computation
    severity: high
    confidence:
      value: 0.88
      rationale: Nested iteration is a known computational cost.
    rationale: Why this rule matters.
    detection: Structural condition a future detector may look for.
    recommendation: Guidance shown to users.
    references:
      - title: Green Software Patterns
        url: https://patterns.greensoftware.foundation/
        authors: [Green Software Foundation]
        year: 2024
    version: "1.0.0"
    tags: [loops, cpu]
    languages: [any]
```

## Required Rule Fields

- `id`: stable unique identifier.
- `name`: short human-readable rule name.
- `description`: concise description.
- `category`: one of `computation`, `io`, `network`, `concurrency`, `memory`, `control_flow`, `exception_handling`, `async`.
- `severity`: one of `info`, `low`, `medium`, `high`, `critical`.
- `confidence`: numeric value or object with `value` and optional `rationale`.
- `rationale`: explanation of why the rule exists.
- `detection`: plain-language structural condition for future detectors.
- `recommendation`: remediation guidance.
- `references`: non-empty list of supporting references.
- `version`: semantic version string such as `1.0.0`.
- `tags`: non-empty list of strings.

## Optional Rule Fields

- `languages`: non-empty list of applicable languages. Defaults to `["any"]`.

## Reference Fields

- `title`: required.
- `url`: optional.
- `authors`: optional list of strings.
- `year`: optional integer greater than or equal to 1900.
- `doi`: optional string.

## Validation

The loader validates required fields, duplicate IDs, enum values, confidence range, semantic versions, reference shape, tags, languages, and malformed YAML.
