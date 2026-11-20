# Code-Carbon: Comprehensive Master Project Documentation

**A Sustainability-First Framework for Carbon-Aware Software Engineering & Predictive Empirical Carbon Estimation**

---

## Table of Contents

1. [Executive Overview & Scientific Purpose](#1-executive-overview--scientific-purpose)
2. [Complete Mathematical Formulation & Scoring Schemes](#2-complete-mathematical-formulation--scoring-schemes)
   - [2.1 Structural Complexity Index (SCI)](#21-structural-complexity-index-sci)
   - [2.2 Energy Smell Score (ESS) & Fuzzy Belief Union](#22-energy-smell-score-ess--fuzzy-belief-union)
   - [2.3 Carbon Impact Risk Score (CIRS) & Physical Carbon Model](#23-carbon-impact-risk-score-cirs--physical-carbon-model)
      - [2.3.1 Three-row code and scheduling comparison](#231-three-row-code-and-scheduling-comparison)
   - [2.4 Runtime and Relative Energy Model](#24-runtime-and-relative-energy-model)
   - [2.5 Hardware Profiling & Reference Compute Power (RCP)](#25-hardware-profiling--reference-compute-power-rcp)
   - [2.6 Carbon Grid Intensity Providers](#26-carbon-grid-intensity-providers)
3. [End-to-End Pipeline Architecture & Data Flow](#3-end-to-end-pipeline-architecture--data-flow)
4. [Complete Repository Directory & Module Index](#4-complete-repository-directory--module-index)
5. [Controlled Benchmark Suite (`experiments/benchmarks_v2/`)](#5-controlled-benchmark-suite-experimentsbenchmarks_v2)
   - [5.1 Category Structure & Program Descriptions](#51-category-structure--program-descriptions)
6. [Empirical Evaluation of Complexity-Based Energy Risk (`experiments/results/calibration_v2/`)](#6-empirical-evaluation-of-complexity-based-energy-risk-experimentsresultscalibration_v2)
   - [6.1 Experimental Methodology & Runtime-Energy Proxy](#61-experimental-methodology--runtime-energy-proxy)
   - [6.2 Correlation Analysis & OLS Calibration Results](#62-correlation-analysis--ols-calibration-results)
   - [6.3 Model Comparison Analysis](#63-model-comparison-analysis)
   - [6.4 5-Fold Cross-Validation Performance](#64-5-fold-cross-validation-performance)
   - [6.5 Predictor Multicollinearity (VIF)](#65-predictor-multicollinearity-vif)
   - [6.6 Exploratory LoopOps Predictor Cross-Validation](#66-exploratory-loopops-predictor-cross-validation)
   - [6.7 Scientific Framing & Response to Reviewer Concerns](#67-scientific-framing--response-to-reviewer-concerns)
   - [6.8 Saturating LoopOps Validation](#68-saturating-loopops-validation)
7. [Public GitHub 30 Repositories Test Corpus (`experiments/results/github_projects/`)](#7-public-github-30-repositories-test-corpus-experimentsresultsgithub_projects)
8. [Docker Configuration, Setup, & Reproducibility Guide](#8-docker-configuration-setup--reproducibility-guide)

---

## 1. Executive Overview & Scientific Purpose

**Code-Carbon** is an academic-grade, publication-oriented research framework designed to analyze Python source code, detect software energy inefficiencies ("energy smells"), and estimate early-stage runtime carbon footprints without requiring runtime execution of target applications.

### Primary Research Motivations:
1. **Early-SDLC Carbon Visibility**: Traditional software carbon tracking relies on dynamic measurement (e.g., RAPL counters during execution) which occurs late in the Software Development Life Cycle (SDLC). Code-Carbon provides predictive, static AST-driven risk estimation during early development.
2. **Empirical Evaluation of Heuristic Indicators**: A controlled empirical calibration experiment evaluates 30 benchmark programs (`experiments/benchmarks_v2/`) against runtime-estimated energy. The separate GitHub corpus is for static analysis only; its repositories are not included in the calibration regression. The raw-backed calibration results demonstrate limited out-of-sample predictive capability (5-fold test $R^2 = -1.2046 \pm 1.1467$), indicating that SCI and CIRS function as transparent static risk indicators rather than direct measurements or universally calibrated physical predictors.
3. **Standards-Compliant Sustainability Modeling**: Integrates Green Software Foundation (GSF) SCI specifications, ISO 31000 risk management exposure frameworks, and Electricity Maps location-based marginal carbon intensities.

---

## 2. Complete Mathematical Formulation & Scoring Schemes

### 2.1 Structural Complexity Index (SCI)

The Structural Complexity Index (SCI) aggregates normalized static complexity metrics into a scalar value in $[0.0, 1.0]$.

#### Normalization Rules:
Raw metrics are normalized using upper bound thresholds defined in `src/complexity/normalizer.py`:
$$\text{CC}_{\text{norm}} = \min\left(\frac{\text{CC}_{\text{raw}}}{50.0}, 1.0\right)$$
$$\text{ND}_{\text{norm}} = \min\left(\frac{\text{ND}_{\text{raw}}}{10.0}, 1.0\right)$$
$$\text{FD}_{\text{norm}} = \min\left(\frac{\text{FD}_{\text{raw}}}{0.20}, 1.0\right)$$

Where:
- $\text{CC}$: Cyclomatic Complexity (number of linearly independent execution paths).
- $\text{ND}$: Maximum Nesting Depth (deepest block indentation level).
- $\text{FD}$: Function Density ($\text{Function Count} / \text{Lines of Code}$).

#### Production Formula:
$$\text{SCI} = 0.50 \cdot \text{CC}_{\text{norm}} + 0.30 \cdot \text{ND}_{\text{norm}} + 0.20 \cdot \text{FD}_{\text{norm}}$$

*Note on Calibration Regression*: The raw-backed rerun on 30 controlled benchmarks yielded normalized absolute regression-coefficient shares of 71.19% for CC, 11.75% for ND, and 17.06% for FD. These are descriptive only: predictors have different observed distributions, and all fitted slopes are negative. The regression provides no variable-importance estimate; held-out predictive power is weak (5-fold cross-validation $R^2 = -1.2046 \pm 1.1467$). The production formula ($0.50 / 0.30 / 0.20$) remains a transparent static risk indicator.

For the latest frozen-timing regression, the CC coefficient p-value is $0.2722$ (the preceding quality-gate-based rerun reported $0.2010$). These comparisons are descriptive only: versions use different timing sources/scales, and fitted slopes are negative. The OLS fit is unstable and does not calibrate the production SCI weights.

---

### 2.2 Energy Smell Score (ESS) & Fuzzy Belief Union

The Energy Smell Score (ESS) quantifies active code-level energy leaks using an **Algebraic T-Conorm Fuzzy Set Belief Union** operator (Klement et al., 2000; Dubois & Prade, 1985).

$$\text{P}_{\text{leak}} = 1.0 - \prod_{r \in R} (1.0 - c_r)$$
$$\text{ESS} = 10.0 \cdot \text{P}_{\text{leak}}$$

Where:
- $R$: Set of distinct detected rule IDs in the source file.
- $c_r = \min(0.9, \max_{f: rule(f)=r} \text{confidence}_f)$: Rule contribution is the maximum finding confidence for that rule, capped at 0.9. Repeated locations of the same rule contribute once; distinct rule types remain separate fuzzy-union terms.
- $\text{P}_{\text{leak}} \in [0.0, 1.0]$: Fuzzy joint possibility of at least one active energy leak.
- $\text{ESS} \in [0.0, 10.0]$: Scaled Energy Smell Score conforming to `ComplexityNormalizer.MAX_ENERGY_SMELL_SCORE`.

---

### 2.3 Carbon Impact Risk Score (CIRS) & Physical Carbon Model

Code-Carbon provides two formulations of CIRS:

#### 1. `CIRS_heuristic`: Internal Heuristic Risk Score ($[0.0, 1.0]$):
Used internally for qualitative risk classification (`VERY_LOW`, `LOW`, `MODERATE`, `HIGH`, `VERY_HIGH`).
$$\text{CIRS}_{\text{heuristic}} = 0.55 \cdot \text{SCI} + 0.45 \cdot \left(\frac{\text{ESS}}{10.0}\right)$$

*Note on CIRS Calibration*: Constrained optimization under the controlled calibration setting assigned weights $w_{\text{SCI}} = 1.0, w_{\text{ESS}} = 0.0$ due to ESS score concentration across benchmark programs. This result reflects the specific constrained experimental context and does not imply that ESS is non-impactful or that the production formula should be altered. The production formula ($0.55 \cdot \text{SCI} + 0.45 \cdot \text{ESS}/10.0$) is retained.

#### 2. `CIRS_research`: Physical Research Carbon Risk Model ($\text{gCO}_2\text{eq/run}$):
Implements ISO 31000 Multiplicative Risk Exposure: $\text{Risk} = \text{Hazard} \times \text{Exposure}$.
$$\text{Hazard } (H) = E_{\text{kwh}} \cdot I = \left(\frac{E_{\text{joules}}}{3,600,000}\right) \cdot I$$
$$\text{Exposure } (Ex) = \text{SCI} \cdot (1.0 + \text{P}_{\text{leak}}) = \text{SCI} \cdot \left(1.0 + \frac{\text{ESS}}{10.0}\right)$$
$$\text{CIRS}_{\text{research}} = H \cdot Ex = \left(\frac{E_{\text{joules}}}{3,600,000} \cdot I\right) \cdot \text{SCI} \cdot \left(1.0 + \frac{\text{ESS}}{10.0}\right)$$

Where:
- $E_{\text{joules}}$: Estimated energy consumption in Joules.
- $I$: Location-based marginal carbon intensity in $\text{gCO}_2\text{eq/kWh}$.

#### 2.3.1 Three-row code and scheduling comparison

The three displayed rows are unweighted modeled footprints on one basis, **modeled gCO$_2$eq/run**:

| Display row | Calculation | API field |
|---|---|---|
| Before · run now | $E_{before}/3{,}600{,}000 \times I_{now}$ | `carbon_before` |
| After · run now | $E_{after}/3{,}600{,}000 \times I_{now}$ | `carbon_after_now` |
| After · green window | $E_{after}/3{,}600{,}000 \times I_{green}$ | `carbon_after_green` |

The code-only, schedule-only, and total percentages use the same unweighted rows and the before row as denominator: `code_only_pct = (carbon_before - carbon_after_now) / carbon_before × 100`; `schedule_only_pct = (carbon_after_now - carbon_after_green) / carbon_before × 100`; `total_pct = (carbon_before - carbon_after_green) / carbon_before × 100`. The API reports `cirs_before` and `cirs_after` separately as **unitless CIRS research risk scores**; CIRS is not used as a row or as the percentage denominator. No fixed illustrative reduction is claimed here; percentages are response-specific and should be recomputed from the returned rows.

---

### 2.4 Runtime and Relative Energy Model

The runtime estimator uses a static, relative model:

$$T_{rel} = \frac{SCI}{\max(HPI,0.01)} \left(1+\frac{\beta \cdot LoopOps}{LoopOps+K}\right), \qquad \beta=2.0,\ K=100.0.$$

`HPI` (Hardware Performance Index) is the arithmetic mean of four normalized hardware scores: physical CPU cores, CPU frequency, RAM capacity, and GPU presence (each normalized to $[0,1]$). `LoopOps` is an AST-derived assumed operation score: nonconstant binary operations contribute 1, calls contribute 2, and each is weighted by $10^{depth}$ for its enclosing loop/comprehension depth. This $10$-iterations-per-level assumption is a static weighting, not a measured iteration count. Recursion is not expanded or weighted by recursive call depth; recursive work is detected separately but is outside this LoopOps estimate.

Modeled energy is $E_{rel}=T_{rel}\times RCP$, reported as **modeled J (relative)**. These estimates support within-model comparisons and are not absolute physical measurements. When a refactoring applies no fix, before/after modeled energy and risk values are identical and the UI/API label the result **“No modeled change.”**

### 2.5 Hardware Profiling & Reference Compute Power (RCP)

Energy estimation references a hardware benchmark profile database (`src/hardware_profile/database.py`). System baseline power uses standard Reference Compute Power ($P_{\text{RCP}} = 55.00$ W).

---

### 2.6 Carbon Grid Intensity Providers

- **Live Provider (`ElectricityMapsProvider`)**: Queries Electricity Maps API v4 for real-time regional carbon grid intensities.
- **Mock Provider (`MockCarbonIntensityProvider`)**: Offline fallback utilizing a diurnal sine wave simulator and regional grid zone database.
- **Global fallback**: When a provider cannot return an intensity, the configured fallback is **435 gCO$_2$eq/kWh**. The source is labeled as fallback in results; it is not a live regional observation.

---

## 3. End-to-End Pipeline Architecture & Data Flow

Static source code is parsed by `PredictivePipeline`, extracting AST nodes, computing Radon structural complexity, detecting energy smells via fuzzy belief union, referencing hardware power baselines, and computing SCI and CIRS risk scores.

---

## 4. Complete Repository Directory & Module Index

- `src/analysis/`: AST visitors and code parsing.
- `src/complexity/`: Radon complexity scoring and normalization.
- `src/detector/`: Energy smell detection engine.
- `src/sustainability/`: Fuzzy ESS and CIRS math engines (`metrics.py`).
- `src/pipeline/`: `PredictivePipeline` orchestrator.
- `src/api/`: FastAPI REST backend server.
- `dashboard/`: React + Vite SPA dark-mode visualizer dashboard.
- `experiments/benchmarks_v2/`: Controlled V2 30-benchmark suite.
- `experiments/results/calibration_v2/`: Final V2 calibration experiment results.

---

## 5. Controlled Benchmark Suite (`experiments/benchmarks_v2/`)

To evaluate metric behavior without runtime confounding, a redesigned controlled benchmark suite of **30 Python programs** (5 per category) was constructed under `experiments/benchmarks_v2/`.

```
experiments/benchmarks_v2/
├── simple_control_flow/    (simple_01.py .. simple_05.py)
├── nested_loops/          (nested_01.py .. nested_05.py)
├── recursion/             (recursion_01.py .. recursion_05.py)
├── function_density/      (func_density_01.py .. func_density_05.py)
├── mixed_cpu/             (mixed_cpu_01.py .. mixed_cpu_05.py)
├── algorithmic_variants/  (algo_01.py .. algo_05.py)
├── benchmark_metadata.csv
└── validate_benchmarks.py
```

### 5.1 Category Structure & Program Descriptions

1. **Simple Control Flow (`simple_control_flow/`)**: Sequential logic, branch chains, and conditional guards.
2. **Nested Loops (`nested_loops/`)**: Systematically varied loop nesting depths (1 to 9).
3. **Recursion (`recursion/`)**: Linear recursion, binary tree traversals, and divide-and-conquer calls.
4. **Function Density (`function_density/`)**: Varied function-to-LOC ratios (from monolithic single-function to micro-functions).
5. **Mixed CPU (`mixed_cpu/`)**: Realistic CPU workloads combining numerical integration, string distance matrices, and Monte Carlo simulations.
6. **Algorithmic Variants (`algorithmic_variants/`)**: Classic algorithmic paradigms including prime sieves, sorting algorithms, and dynamic programming.

All 30 benchmark workloads are deterministic and CPU-oriented, containing zero sleep operations, disk I/O, or network calls. From the five frozen runs per benchmark in `raw_results.csv`, runtimes range from **0.856506 s to 3.474497 s** (mean **1.569928 s**). The nested-loop family includes materially different iteration schedules: `nested_01` performs about 35 million simple iterations, while `nested_05` uses a depth-9 structure with a small base range (about 8^8 body visits). Their runtimes therefore do not imply comparable iteration counts. LoopOps weights AST operations by the assumed factor 10^depth; this is a structural heuristic and not an observed iteration count.

---

## 6. Empirical Evaluation of Complexity-Based Energy Risk (`experiments/results/calibration_v2/`)

### 6.1 Experimental Methodology & Runtime-Energy Proxy

Each of the 30 benchmark programs was executed **5 times** in isolated subprocesses using high-precision timers (`time.perf_counter()`), yielding 150 total execution runs.

The dependent variable was evaluated as a **runtime-estimated energy proxy**:
$$E_{\text{proxy}} = 55.0\text{ W} \times t_{\text{runtime}}$$

It is a runtime-based energy proxy, not a direct electrical power meter measurement.

---

### 6.2 Correlation Analysis & OLS Calibration Results

The earlier calibration run recollected benchmark timings. Its regression used means from the quality-gate timing file while separately writing the 150 raw calibration-run timings. This was a data-source mismatch, not an effect of ESS on SCI: the OLS target is energy and the predictors are CC, ND, and FD. The current analysis aggregates the frozen `raw_results.csv` runs directly. In the current 30-row data, raw and normalized CC, ND, FD, LOC, and smell count agree exactly between the frozen raw records and the quality-gate structural metrics (maximum absolute difference 0.0); these fields did not change in the raw-timing correction. The pre-rerun V2 aggregate is not preserved, so a structural-field diff against that older run is unverified. See §8.2 for timing freeze and reproducibility details.

$$E_{\text{proxy}} = 112.0013 - 79.1455(\text{CC}) - 13.0663(\text{ND}) - 18.9707(\text{FD})$$

**Fit Statistics**: $R^2 = 0.0727$, Adjusted $R^2 = -0.0343$, MAE = 11.9115 J, RMSE = 21.1973 J.

| Variable | Raw Beta | Std Error | t-statistic | p-value | 95% CI |
|:---|---:|---:|---:|---:|:---|
| Intercept | 112.0013 | 20.6694 | 5.4187 | 0.0000 | [69.5148, 154.4878] |
| CC | -79.1455 | 70.5458 | -1.1219 | 0.2722 | [-224.1545, 65.8635] |
| ND | -13.0663 | 30.0133 | -0.4354 | 0.6669 | [-74.7595, 48.6269] |
| FD | -18.9707 | 23.6214 | -0.8031 | 0.4292 | [-67.5252, 29.5838] |

Normalized absolute coefficient contributions are CC 71.19%, ND 11.75%, and FD 17.06%; these are descriptive and are not production SCI weights.

The OLS results vary materially across three data/timing versions; all predictor slopes remain negative, but coefficients and fit are unstable. Scales and timing sources differ, so this table is descriptive only.

| Version | Intercept | βCC | βND | βFD | R² | CC p-value |
|---|---:|---:|---:|---:|---:|---:|
| Earlier published aggregate | 105.7428 | -104.2888 | -3.3139 | -8.7816 | 0.0961 | 0.1253 |
| Intermediate quality-gate timing | 113.4301 | -93.5794 | -7.9569 | -15.5400 | 0.0793 | 0.2010 |
| Current frozen raw timing | 112.0013 | -79.1455 | -13.0663 | -18.9707 | 0.0727 | 0.2722 |

Earlier log-damped paired validation results were reported as Spearman ρ=0.821, then ρ=0.22 on a subsequent run. A prior short-run saturating LoopOps validation produced ρ=-0.014; the stricter 0.5-second/20-repeat validation reported below produced ρ=0.082 (p=0.846). These protocols are not directly comparable. The earlier validation artifacts and exact run commands are not preserved here, so those historical values are reported as previously documented and remain unverified in this audit.

### 6.3 Model Comparison Analysis

| Model | MAE (J) | RMSE (J) | $R^2$ | Pearson $r$ | Spearman $\rho$ |
|:---|---:|---:|---:|---:|---:|
| Original SCI | 11.6619 | 21.3824 | 0.0565 | -0.2376 | -0.3611 |
| Calibrated SCI | 11.9115 | 21.1973 | 0.0727 | 0.2697 | 0.3731 |
| Original CIRS | 11.6549 | 22.0057 | 0.0006 | 0.0254 | -0.2548 |
| Calibrated CIRS | 11.6619 | 21.3824 | 0.0565 | -0.2376 | -0.3611 |

The constrained calibration selected $w_{SCI}=1.0$, $w_{ESS}=0.0$ (calibration Pearson $R^2=0.0565$). Therefore calibrated CIRS equals the **original SCI** predictor in this calibration, as reflected by their identical row values.

### 6.4 5-Fold Cross-Validation Performance

| Fold | Train | Test | Intercept | $\beta_{CC}$ | $\beta_{ND}$ | $\beta_{FD}$ | MAE (J) | RMSE (J) | Test $R^2$ | Pearson $r$ | Spearman $\rho$ |
|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 24 | 6 | 109.4625 | -100.5894 | -10.9313 | -8.6887 | 12.8560 | 18.7642 | -0.1108 | 0.2531 | 0.4286 |
| 2 | 24 | 6 | 95.8574 | -53.2349 | -10.3997 | -5.3708 | 23.9137 | 42.1643 | -0.1703 | 0.0681 | 0.4286 |
| 3 | 24 | 6 | 118.8487 | -39.9243 | -26.0756 | -30.1337 | 15.0709 | 19.4894 | -1.3703 | 0.0330 | 0.3714 |
| 4 | 24 | 6 | 116.4801 | -94.5372 | -13.0085 | -24.0319 | 5.6570 | 7.6902 | -1.1003 | 0.5077 | 0.4857 |
| 5 | 24 | 6 | 117.3908 | -106.2246 | 7.6511 | -25.9294 | 12.1538 | 14.7620 | -3.2711 | -0.3550 | -0.2571 |
| Mean $\pm$ SD | 24 | 6 | 111.61 $\pm$ 8.51 | -78.90 $\pm$ 26.98 | -10.55 $\pm$ 10.76 | -18.83 $\pm$ 9.89 | 13.9303 $\pm$ 5.8945 | 20.5740 $\pm$ 11.5790 | -1.2046 $\pm$ 1.1467 | 0.1014 $\pm$ 0.2836 | 0.2914 $\pm$ 0.2767 |

### 6.5 Predictor Multicollinearity (VIF)

Variance Inflation Factor analysis yields:
- $\text{VIF}(\text{CC}) = 1.0444$
- $\text{VIF}(\text{ND}) = 1.3790$
- $\text{VIF}(\text{FD}) = 1.3293$

**Finding**: All VIF values are below 1.4, indicating no substantial multicollinearity among the predictors (low multicollinearity).

---

### 6.6 Exploratory LoopOps Predictor Cross-Validation

The comparison below uses the frozen five-run `raw_results.csv` (150 measurements, 30 benchmarks), with the same stratified five-fold split. Baseline mean-fold R² matches §6.4; pooled out-of-fold (OOF) R² is a separate statistic and should not be compared to the mean of fold R² values.

| Model | OOF MAE (J) | OOF RMSE (J) | OOF R² | Mean fold R² | Nested-loop OOF R² |
|---|---:|---:|---:|---:|---:|
| CC + ND + FD | 13.9303 | 23.6085 | -0.1502 | -1.2046 | -0.3160 |
| CC + ND + FD + raw LoopOps | 10787.1895 | 59006.1996 | -7185291.6300 | -68241025.1276 | -100309414.1024 |
| CC + ND + FD + log10(1 + LoopOps) | 15.5135 | 21.5042 | 0.0457 | -3.1971 | -0.0128 |

The log-transformed predictor does not improve mean fold performance. Raw LoopOps is numerically unstable because its assumed-depth weighting is highly skewed. The nested-only score is descriptive (n=5). Full outputs: `experiments/results/loopops_cv/report.md`.

### 6.7 Scientific Framing & Response to Reviewer Concerns

The SCI and CIRS coefficients are initially defined as heuristic weights to provide a transparent composite risk indicator. An empirical calibration experiment was conducted to evaluate whether these static metrics could reliably explain runtime-estimated energy. The frozen raw-backed calibration showed limited predictive capability (mean test $R^2 = -1.2046$), indicating that the coefficients should not be interpreted as universally calibrated physical relationships.

This provides an important scientific insight: **static complexity metrics alone were insufficient to provide reliable out-of-sample prediction of runtime-estimated energy under controlled conditions**.

Therefore, SCI and CIRS are retained as transparent static risk indicators rather than being interpreted as direct or universally calibrated energy or carbon measurements.

The V2 benchmark quality gate was completed before coefficient calibration. The subsequent calibration experiment was executed using the validated V2 benchmark suite.

### 6.8 Saturating LoopOps Validation

The candidate multiplier uses specified constants $\beta=2.0$ and $K=100.0$: $1 + \beta \cdot \text{LoopOps}/(\text{LoopOps}+K)$. This rerun enforced at least 0.5 s per invocation, 20 repeats per positive version, and three independent 20-repeat rounds per negative control; it reports medians and IQRs. Positive-pair direction agreement was 8/8, but rank agreement was negligible (Spearman $\rho=0.082$, $p=0.846$, $n=8$), so the audit row is **ran; inconclusive**. Model-predicted drops were 7.17%–10.91%; observed positive-pair medians ranged from 26.67% to 88.01%. Across six negative-control rounds, absolute median-drop noise ranged **0.94%–7.18%**, reaching the lower edge of the modeled range. These results do not establish that the modeled drop magnitudes predict observed runtime changes. The earlier short-run control noise (7.51%, 4.35%; later 22.95%, 4.39%) used a different protocol and is retained only as historical context. On the strict rerun, Windows power mode was Balanced, processor state settings were minimum 5% and maximum 100%, CPU frequency sampled at 1520 MHz, and CPU load at run boundaries was 16.2%/12.9%; settings were not pinned and load was not monitored continuously. 

| Positive pair | Modeled drop | Measured median drop (IQR) |
|---|---:|---:|
| sum_weights | 10.91% | 53.56% (49.06–57.80) |
| max_limits | 10.91% | 59.85% (59.23–60.52) |
| sin_angle | 10.91% | 52.53% (47.36–53.08) |
| zfill_text | 7.64% | 30.21% (26.26–33.95) |
| dict_lookup | 10.91% | 26.67% (21.93–32.63) |
| list_copy | 7.17% | 55.91% (52.07–57.27) |
| string_replace | 7.64% | 52.68% (49.57–53.69) |
| round_config | 10.91% | 88.01% (87.71–88.46) |

| Negative control | Round 1 median | Round 2 median | Round 3 median |
|---|---:|---:|---:|
| constant_arithmetic_control | 2.42% | -5.29% | 7.18% |
| noop_rewrite_control | -0.94% | -2.74% | 2.00% |

Full raw samples are in `experiments/results/saturating_loopops_validation/new_pairs.csv`.

---

## 7. Public GitHub 30 Repositories Test Corpus (`experiments/results/github_projects/`)

The audited corpus analyzes **one pinned primary Python source file per repository**, not each complete repository. It covers 30 repositories across 6 domain categories, with 30/30 successful static analyses, 47,406 genuine LOC (mean 1,580.2 LOC per selected file), and 8 CLI suites / 22 library or framework modules. The mean SCI is **0.5297**, mean ESS is **8.3314 / 10** (0.8331 normalized), and mean heuristic CIRS is **0.6662**. These figures use the primary pinned source paths in `experiments/audit_github_corpus.py`; they are static-analysis results, not runtime measurements. The previous documentation's means (SCI 0.2315, CIRS 0.5480) are not reproduced by the preserved legacy analysis CSV, which averages 0.1263 SCI, 0.0991 normalized ESS, and 0.1141 CIRS over 6,782 selected LOC. The selected-source paths changed between corpus versions, raising measured LOC per selected file across the 30 repositories from 6,782 to 47,406 in aggregate (226.1→1,580.2 mean LOC per repository). The SCI formula and weights remain $0.50 CC + 0.30 ND + 0.20 FD$; the strongest evidenced cause is different selected source paths and larger structural inputs, not a new SCI formula. The per-repository raw ESS distribution is: mean 8.3314/10, SD 3.3506, median 9.9000, IQR 9.0000–9.9472, range 0–9.9947; four repositories have ESS 0. Spearman correlation between raw ESS and selected-file LOC is ρ=0.5162 (p=0.00350, n=30), a descriptive association. Section 7 reports `CIRS_heuristic`; it does not report the energy-and-intensity-based `CIRS_research`. The 30 canonical owner/repository names are the same; the old URLs for `Textualize/rich` and `fastapi/typer` became `textualize/rich` and `tiangolo/typer`. Because the dataset behind the old prose means is unavailable and its metrics conflict with the preserved legacy CSV, an exact numeric decomposition of 0.2315→0.5297 is unverified.

All 30 canonical owner/repository names are retained. There are 28 exact URL strings in common; the other two URLs changed from `Textualize/rich` to `textualize/rich` (case normalization) and `fastapi/typer` to `tiangolo/typer` (repository-owner URL correction). The full old/new URL lists and LOC comparison are recorded in `docs/AUDIT_REPORT.md`.

---

## 8. Docker Configuration, Setup, & Reproducibility Guide

### 8.1 Docker Setup
```bash
docker-compose up --build
```

### 8.2 Reproducibility Commands

#### 1. Run the completed non-API test suite (123 tests):
```powershell
$env:PYTHONPATH="src"
python -m pytest -q --ignore=tests/test_api_endpoints.py
```
The API endpoint suite is **unverified in the sandbox**: TestClient blocks while creating the asyncio self-pipe (`socket._fallback_socketpair`) before dispatching the first endpoint request.

#### 2. Run Quality Gate Evaluation:
```powershell
python experiments/run_v2_quality_gate.py
```

#### 3. Run V2 Empirical Calibration Experiment:
```powershell
python experiments/run_v2_calibration_experiment.py
```
This reuses the frozen `experiments/results/calibration_v2/raw_results.csv` by default and validates `raw_results.csv.sha256`; it does not execute benchmarks. To recollect all five runs per benchmark and replace the frozen data, explicitly pass `--recollect-timings`.

Per-benchmark run-to-run variability is reported as sample coefficient of variation (sample SD / mean) in `experiments/results/calibration_v2/run_to_run_variability.csv`. The frozen 150-run set has CV min/median/mean/max of 0.28% / 1.10% / 1.30% / 4.43%.

#### 4. Run Final Calibration & Paper Artifact Consistency Generator:
```powershell
python experiments/finalize_v2_calibration.py
```

All 16 consistency checks will execute automatically, verifying paper alignment, table formatting, OLS metrics, and ZIP package completeness.

#### 5. Run saturating LoopOps paired validation:
```powershell
$env:PYTHONPATH="src"
python experiments/run_saturating_loopops_validation.py
```
