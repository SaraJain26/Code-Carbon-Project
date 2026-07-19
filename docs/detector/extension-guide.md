# Adding a New Detector

Implement:

- CandidateExtractor
- RuleEvaluator
- FindingGenerator

Instantiate:

EnergySmellDetector(
    extractor,
    evaluator,
    generator
)

No modifications to the framework should be necessary.

This follows the Open/Closed Principle.