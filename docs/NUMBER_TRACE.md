# Dashboard number trace

Inventory traced from `dashboard/src/App.tsx` and `src/api/main.py`. Static text, timestamps, line numbers, and chart axes are included where the displayed numeric value is user data. Tooltip-only values are listed with their chart.

## Home

| Displayed label | Unit | API field | Computing function |
|---|---|---|---|
| Total files / analyzed / errors | files | `total_files`, `successful_files`, `error_files` | `analyze_project` |
| Total SLOC | SLOC | `total_lines_of_code` | sum of file `lines_of_code` in `analyze_project` |
| Analyzed in | seconds | `total_analysis_time_sec` | wall clock in `analyze_project` |
| Total Files | files | `total_files` | `analyze_project` |
| Finding locations | findings, plus rule instances | `total_findings`, `total_rule_count` | sums per-file `findings_count` and `rule_count` |
| Mean SCI/ESS/CIRS per file | SCI index / ESS out of 10 / unitless CIRS | `avg_sci`, `avg_ess`, `avg_cirs` | macro averages in `analyze_project` |
| Project energy score | modeled J (relative) | `total_energy_joules` | sum of per-file `energy_joules` |
| Sum of risk-weighted scores | unitless CIRS | `total_cirs` | sum of per-file `cirs` |
| Grid intensity | gCO₂eq/kWh | `carbon_intensity` | selected file's carbon metadata in `analyze_project` |
| Zone / source type / provider | zone key / category / provider name | `carbon_zone`, `carbon_source_type`, `carbon_source` | `run_single_file_analysis` carbon metadata |
| Project file rows: SLOC, rules, finding locations, SCI, ESS, risk score, modeled J | SLOC / counts / index / score / relative modeled J | `files[].lines_of_code`, `rule_count`, `findings_count`, `sci`, `ess`, `cirs`, `energy_joules` | `analyze_project` per-file worker |

## Project Results and File Results

| Displayed label | Unit | API field | Computing function |
|---|---|---|---|
| Estimated Energy | modeled J (relative) | `pipeline_raw.energy_result.energy.energy_joules` | `EnergyEstimator.estimate` |
| CIRS research | unitless score | `research_metrics.carbon_impact_risk_score` | `ResearchSustainabilityMetrics.compute_carbon_impact_risk_score` |
| ESS | score / 10 (one capped contribution per distinct rule type) | `research_metrics.energy_smell_score`; before/after values in `post_refactor_estimation.ess_*` | `ResearchSustainabilityMetrics.compute_energy_smell_score` |
| Individual Findings | finding locations | `energy_smell_report.summary.total_findings` | `ReportStatistics.from_findings` |
| CC / ND / FD / SLOC / SCI | decision paths / max depth / functions per SLOC / SLOC / index | `complexity_metrics` and `complexity_score.structural_complexity_index` | `ComplexityMetricsExtractor.extract`, `ComplexityEngine.analyze` |
| Recommendation count / priority score | recommendations / unitless heuristic | `recommendations.recommendations`, each `priority_score` | `RecommendationEngine.generate`, `RecommendationPrioritizer` |
| Code comparison rows | field-specific units | `post_refactor_estimation` fields | `run_single_file_analysis` comparison calculations |
| Carbon footprint | modeled gCO₂eq/run (one modeled run per file; project value sums those runs) | `total_energy_kwh`, `carbon_intensity` | `energy_joules / 3,600,000 * intensity` in dashboard |

## Impact

| Displayed label | Unit | API field | Computing function |
|---|---|---|---|
| Energy, SCI, ESS, CIRS before → after | modeled J (relative), index, score / 10, unitless CIRS | `post_refactor_estimation.energy_*`, `sci_*`, `ess_*`, `cirs_*` | `run_single_file_analysis` |
| Energy smells | actionable findings (confidence ≥ 0.5) and summed confidence burden | `smells_*`, `smell_burden_*` | threshold/count and confidence sum in `run_single_file_analysis` |
| Measured Speedup | percentage, or nonnumeric reliability state | `measured_reduction_percent`, `measurement_reliability` | `SandboxedRuntimeExecutor.measure_comparison` |
| Resolved Energy Smell Rules | rules resolved / rules before | `resolved_rule_count`, `rule_count_before` | rule-ID set difference in `run_single_file_analysis` |
| Finding comparison | rules and confidence (0–1) | `findings_comparison[].confidence_*`, `.is_resolved` | `run_single_file_analysis` |

## Green Scheduling

| Displayed label | Unit | API field | Computing function |
|---|---|---|---|
| Current / lowest forecast intensity | gCO₂eq/kWh | `current_carbon_intensity`, `lowest_forecast_intensity` | `CarbonEstimationEngine.forecast` / best forecast selection |
| Three-row footprint scenarios | modeled gCO₂eq/run | `carbon_before`, `carbon_after_now`, `carbon_after_green` | `energy_J / 3,600,000 * intensity`; all percentage reductions are recomputed from these displayed rows |
| CIRS risk score | unitless | `cirs_before`, `cirs_after`; detailed values also in `post_refactor_estimation.cirs_*` | `ResearchSustainabilityMetrics.compute_carbon_impact_risk_score` |
| Percentage reductions | percent | `code_only_pct`, `schedule_only_pct`, `total_pct` | `run_single_file_analysis` |
| Recommended execution time / hourly chart | ISO timestamp / gCO₂eq/kWh | `recommended_execution_time`, `hourly_forecasts[].carbon_intensity` | `/forecast` |

## Untraced numbers and unit inconsistencies

- Chart priority axes display a presentation-scaled priority score; the tooltip provides the raw `priority_score`. The chart's transformed `displayScore` conversion is not labeled with a unit in the UI.
- Impact now labels unweighted physical estimates “modeled gCO₂eq/run”; CIRS before/after remains separately labeled as a unitless exposure-weighted score. Grid intensity remains gCO₂eq/kWh.
- Some chart numeric axes inherit values from transformed datasets without an explicit axis unit; hover tooltips include the source value and unit where implemented.
- Project file rows now use `pipeline_raw.complexity_metrics.lines_of_code` (Radon SLOC), matching the File Results SLOC measure.

Finding-location counts use the detector finding locations consistently on Project Results (`total_findings` / per-file `findings_count`), File Results (`summary.total_findings`), and Impact (`finding_locations_before/after`). “Distinct rule IDs resolved” is a different unit and is explicitly labeled as such.

Consistent energy labels use “modeled J (relative)” on file, project, and comparison views. Carbon intensity is labeled gCO₂eq/kWh throughout.
