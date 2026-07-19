# Energy Knowledge Base Architecture

The Energy Knowledge Base (EKB) is a detector-independent catalog of energy-related software engineering knowledge. It describes energy smells, their rationale, confidence, citations, and recommendations.

The EKB does not inspect ASTs, match code patterns, score complexity, estimate carbon, or schedule workloads.

## Package Name Rationale

The implementation uses `src/knowledge` rather than `src/ekb`.

`knowledge` is a clearer long-term domain package name. The acronym EKB describes the subsystem, while the package can later contain other knowledge assets such as taxonomies, mappings, empirical datasets, or calibration metadata.

## Components

```text
src/knowledge/
  models.py          # Rule dataclasses and enums
  loader.py          # YAML loading and validation
  repository.py      # Queryable in-memory rule repository
  validation.py      # EKB validation errors
  rules/
    energy_rules.yaml
```

## Dependency Direction

```text
loader -> models
loader -> validation
repository -> models
repository -> validation
```

The EKB has no dependency on the static analysis engine or future detector modules. Future detectors should depend on the EKB, not the other way around.

## Future Integration

The Energy Smell Detection Engine should query `RuleRepository` for rule metadata, then map detector findings to rule IDs. Detection logic should remain outside the EKB.
