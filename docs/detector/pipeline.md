# Detection Pipeline

The framework separates detection into four stages.

## Stage 1

Extract candidates from the static analysis output.

## Stage 2

Evaluate those candidates.

This stage may modify confidence or reject candidates.

## Stage 3

Generate EnergyFinding objects.

## Stage 4

Aggregate findings into an EnergySmellReport.

This architecture allows each stage to evolve independently.