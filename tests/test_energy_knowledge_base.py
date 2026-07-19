import tempfile
import unittest
from pathlib import Path

from knowledge import RuleCategory, RuleLoader, RuleRepository, RuleSeverity, RuleValidationError


VALID_RULE_YAML = """
schema_version: "1.0"
rules:
  - id: EKB-TEST-001
    name: Test rule
    description: A valid rule used by tests.
    category: computation
    severity: medium
    confidence:
      value: 0.75
      rationale: Test rationale.
    rationale: This rule exists to verify loading.
    detection: Detect structurally relevant source features.
    recommendation: Prefer a more efficient implementation.
    references:
      - title: Test Reference
        url: https://example.com/reference
        authors: [Researcher]
        year: 2024
    version: "1.0.0"
    tags: [test, computation]
    languages: [any]
"""


class EnergyKnowledgeBaseTest(unittest.TestCase):
    def test_load_default_rules(self) -> None:
        rules = RuleLoader().load_default_rules()

        self.assertGreaterEqual(len(rules), 10)
        self.assertTrue(any(rule.id == "EKB-COMP-001" for rule in rules))
        self.assertTrue(all(rule.references for rule in rules))

    def test_load_valid_rule_file(self) -> None:
        path = self._write_temp_rule_file(VALID_RULE_YAML)

        rules = RuleLoader().load_file(path)

        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].id, "EKB-TEST-001")
        self.assertEqual(rules[0].category, RuleCategory.COMPUTATION)
        self.assertEqual(rules[0].severity, RuleSeverity.MEDIUM)
        self.assertEqual(str(rules[0].version), "1.0.0")

    def test_duplicate_ids_are_rejected_across_files(self) -> None:
        path_one = self._write_temp_rule_file(VALID_RULE_YAML)
        path_two = self._write_temp_rule_file(VALID_RULE_YAML)

        with self.assertRaises(RuleValidationError) as context:
            RuleLoader().load_files([path_one, path_two])

        self.assertIn("Duplicate rule id 'EKB-TEST-001'", str(context.exception))

    def test_missing_required_field_is_reported(self) -> None:
        invalid_yaml = VALID_RULE_YAML.replace("    recommendation: Prefer a more efficient implementation.\n", "")
        path = self._write_temp_rule_file(invalid_yaml)

        with self.assertRaises(RuleValidationError) as context:
            RuleLoader().load_file(path)

        self.assertIn("missing required field 'recommendation'", str(context.exception))

    def test_invalid_enum_confidence_version_and_reference_are_reported(self) -> None:
        invalid_yaml = VALID_RULE_YAML.replace("category: computation", "category: invalid")
        invalid_yaml = invalid_yaml.replace("severity: medium", "severity: urgent")
        invalid_yaml = invalid_yaml.replace("value: 0.75", "value: 1.5")
        invalid_yaml = invalid_yaml.replace('version: "1.0.0"', 'version: "one.two"')
        invalid_yaml = invalid_yaml.replace("title: Test Reference", "title: ''")
        path = self._write_temp_rule_file(invalid_yaml)

        with self.assertRaises(RuleValidationError) as context:
            RuleLoader().load_file(path)

        message = str(context.exception)
        self.assertIn("category has invalid value", message)
        self.assertIn("severity has invalid value", message)
        self.assertIn("confidence.value", message)
        self.assertIn("Version parts must be integers", message)
        self.assertIn("references[0].title", message)

    def test_malformed_yaml_is_reported(self) -> None:
        path = self._write_temp_rule_file("rules:\n  - id: [unterminated\n")

        with self.assertRaises(RuleValidationError) as context:
            RuleLoader().load_file(path)

        self.assertIn("Malformed YAML", str(context.exception))

    def test_repository_queries(self) -> None:
        repository = RuleRepository(RuleLoader().load_default_rules())

        self.assertIsNotNone(repository.get("EKB-NET-001"))
        self.assertGreaterEqual(len(repository.by_category(RuleCategory.NETWORK)), 2)
        self.assertGreaterEqual(len(repository.by_severity(RuleSeverity.HIGH)), 1)
        self.assertGreaterEqual(len(repository.by_tag("loops")), 1)
        self.assertEqual(len(list(repository)), len(repository))

    def test_repository_rejects_duplicate_ids(self) -> None:
        rules = RuleLoader().load_file(self._write_temp_rule_file(VALID_RULE_YAML))

        with self.assertRaises(RuleValidationError):
            RuleRepository([rules[0], rules[0]])

    def _write_temp_rule_file(self, content: str) -> Path:
        temp_dir = Path(tempfile.mkdtemp())
        path = temp_dir / "rules.yaml"
        path.write_text(content, encoding="utf-8")
        return path


if __name__ == "__main__":
    unittest.main()
