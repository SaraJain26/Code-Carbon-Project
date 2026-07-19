# EKB Repository Design

`RuleRepository` is an in-memory query interface over typed `EnergyRule` objects.

## Supported Queries

```python
from knowledge import RuleLoader, RuleRepository, RuleCategory, RuleSeverity

rules = RuleLoader().load_default_rules()
repository = RuleRepository(rules)

repository.get("EKB-NET-001")
repository.require("EKB-NET-001")
repository.by_category(RuleCategory.NETWORK)
repository.by_severity(RuleSeverity.HIGH)
repository.by_tag("loops")
list(repository)
```

## Design Notes

The repository keeps indexes by ID, category, severity, and tag. These indexes support current lookups and leave room for future filtering by confidence, language, version, rule set, or research experiment.

The repository rejects duplicate IDs to protect stable detector-to-rule mappings.
