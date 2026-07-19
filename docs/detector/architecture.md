# Energy Smell Detection Framework

## Objective

The detector framework converts static analysis output into energy smell findings using a modular pipeline.

The framework is intentionally independent of any specific detection algorithm.

## Pipeline

AnalysisResult

↓

CandidateExtractor

↓

RuleEvaluator

↓

FindingGenerator

↓

EnergySmellReport

## Design Principles

- Separation of concerns
- Plugin-based architecture
- Detector-independent framework
- Strongly typed models
- Extensible interfaces
- Research reproducibility

## Responsibilities

### CandidateExtractor

Produces possible rule candidates from an AnalysisResult.

### RuleEvaluator

Evaluates candidates against rule metadata.

### FindingGenerator

Produces final EnergyFinding objects.

### EnergySmellDetector

Coordinates the pipeline.

It does not implement smell detection itself.