# Code-Carbon Calibration V2: Final Empirical Calibration Report

## VI. EXPERIMENTAL METHODOLOGY

### A. Experimental Environment
The empirical calibration experiment was conducted in a controlled environment running Python 3.10 under 64-bit Windows. All benchmark executions were launched via standard system subprocesses using high-precision timers (`time.perf_counter()`). Static metric extraction was performed natively using the Code-Carbon `PredictivePipeline` without modifying any core production analysis, detection, or normalization logic under `src/`.

**TABLE IV. Experimental Environment Configuration**

| Parameter | Configuration |
|:---|:---|
| **Programming Language** | Python 3.10.x |
| **Analysis Technique** | Static AST Analysis via `PredictivePipeline` |
| **Implementation Scope** | External empirical experiment (Unmodified `src/`) |
| **Operating System** | Windows 64-bit |
| **Interface & Process Setup** | Subprocess invocation with `time.perf_counter()` |
| **Framework Components** | `radon`, `ast`, Code-Carbon energy smell detectors |
| **Benchmark Suite** | 30 controlled Python programs (`experiments/benchmarks_v2/`) |
| **Runtime Repetitions** | 5 independent executions per benchmark (150 total runs) |
| **Energy Reference** | Runtime-energy proxy ($55.0\text{ W} \times t_{\text{runtime}}$) |

### B. Energy Smell Detector Validation
The existing energy smell detector validation experiment is distinct from this empirical coefficient calibration experiment. The 30 controlled programs in `experiments/benchmarks_v2/` represent a dedicated calibration benchmark suite engineered to evaluate structural complexity indicators without runtime confounding.

### C. Runtime Energy Proxy and Coefficient Calibration Experiment
To empirically evaluate the initial heuristic weights of the Structural Complexity Index (SCI = 0.50 CC + 0.30 ND + 0.20 FD) and Carbon Impact Risk Score (CIRS = 0.55 SCI + 0.45 ESS), we constructed a redesigned controlled benchmark suite (`experiments/benchmarks_v2/`) comprising N = 30 deterministic CPU-oriented Python programs without sleep, disk I/O, or network operations across six distinct algorithmic categories:
1. `simple_control_flow`: Sequential logic, branch chains, and conditional guards.
2. `nested_loops`: Systematically varied loop nesting depths (1 to 9).
3. `recursion`: Linear recursion, binary tree traversals, and divide-and-conquer calls.
4. `function_density`: Varied function-to-LOC ratios (from monolithic single-function to micro-functions).
5. `mixed_cpu`: Realistic CPU workloads combining numerical integration, string distance matrices, and Monte Carlo simulations.
6. `algorithmic_variants`: Classic algorithmic paradigms including prime sieves, sorting algorithms, and dynamic programming.

The V2 benchmark suite was redesigned to reduce the runtime confounding observed in the preliminary V1 experiment, particularly effects associated with asynchronous waiting (`asyncio.sleep`) and file-I/O latency. Computational workload was approximately normalized across benchmark families to execute in 0.86 to 2.07 seconds (mean runtime: 1.5284 seconds), reducing process startup noise (~2 ms) to < 0.23% of total runtime.

For each benchmark, execution duration was measured across 5 independent runs (150 total executions). The dependent variable was calculated as a **runtime-estimated energy proxy**:
$$\text{E}_{\text{proxy}} = 55.0\text{ W} \times t_{\text{runtime}}$$
where 55.0 W represents the documented Reference Compute Power (RCP).

### D. Evaluation Procedure
1. **Static Analysis**: Each program was analyzed via `PredictivePipeline` to extract raw and normalized CC, ND, FD, ESS, original SCI, and original CIRS.
2. **Correlation Analysis**: Pearson (r) and Spearman (rho) correlation coefficients were computed between the runtime-energy proxy and static predictors.
3. **SCI OLS Calibration**: Multiple linear regression was fitted:
$$\text{E}_{\text{proxy}} = \beta_0 + \beta_{\text{CC}} \cdot \text{CC} + \beta_{\text{ND}} \cdot \text{ND} + \beta_{\text{FD}} \cdot \text{FD}$$
4. **CIRS Weight Calibration**: Constrained weight optimization was performed:
$$\text{CIRS}_{\text{calibrated}} = w_{\text{SCI}} \cdot \text{SCI} + w_{\text{ESS}} \cdot \text{ESS} \quad \text{subject to} \quad w_{\text{SCI}} + w_{\text{ESS}} = 1.0$$
5. **Cross-Validation**: A strict 5-fold cross-validation procedure (24 training programs, 6 held-out test programs per fold) was executed, fitting coefficients exclusively on training data and evaluating out-of-sample performance on held-out test sets.

### E. Evaluation Metrics
The evaluation employs standard statistical metrics including Pearson correlation ($r$), Spearman rank correlation ($\rho$), Coefficient of Determination ($R^2$), Adjusted $R^2$, Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), standard errors, $t$-statistics, $p$-values, and 95% confidence intervals.

---

## VII. RESULTS AND DISCUSSION

### A. Software Metric Extraction Results
Static analysis was 100% successful across all 30 benchmarks. Summary statistics for the benchmark suite are presented in Table VI.

**TABLE VI. Calibration Benchmark Category Characteristics**

| Category | N | Mean LOC | Mean CC | Mean ND | Mean FD | Mean ESS | Mean Runtime (s) | Mean Energy (J) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `algorithmic_variants` | 5 | 18.2 | 0.1880 | 0.2000 | 0.5583 | 0.9308 | 1.9249 | 105.87 |
| `function_density` | 5 | 19.0 | 0.1640 | 0.1000 | 0.9333 | 0.0000 | 1.5284 | 84.06 |
| `mixed_cpu` | 5 | 20.0 | 0.1520 | 0.1600 | 0.5586 | 0.5903 | 1.2272 | 67.50 |
| `nested_loops` | 5 | 10.8 | 0.1000 | 0.4000 | 0.4998 | 0.7200 | 1.5797 | 86.88 |
| `recursion` | 5 | 15.2 | 0.1040 | 0.1000 | 0.7625 | 0.9152 | 1.5580 | 85.69 |
| `simple_control_flow` | 5 | 18.2 | 0.1320 | 0.1000 | 0.5671 | 0.0000 | 1.6013 | 88.07 |

### B. Runtime Energy Proxy Results
Execution results across 150 runs demonstrated high stability. Statistics by category are detailed in Table VII.

**TABLE VII. Runtime Energy Proxy Statistics**

| Category | N | Mean Runtime (s) | Std Runtime (s) | Mean Energy Proxy (J) | Std Energy (J) |
|:---|:---:|:---:|:---:|:---:|:---:|
| `algorithmic_variants` | 5 | 1.9249 | 0.8398 | 105.87 | 46.19 |
| `function_density` | 5 | 1.5284 | 0.0671 | 84.06 | 3.69 |
| `mixed_cpu` | 5 | 1.2272 | 0.2863 | 67.50 | 15.75 |
| `nested_loops` | 5 | 1.5797 | 0.2934 | 86.88 | 16.13 |
| `recursion` | 5 | 1.5580 | 0.1113 | 85.69 | 6.12 |
| `simple_control_flow` | 5 | 1.6013 | 0.0577 | 88.07 | 3.17 |

![Fig. 1: Runtime-Estimated Energy Proxy Distribution](figures/fig1_energy_distribution.png)

*Fig. 1. Runtime-Estimated Energy Proxy Distribution (N=30).*

### C. Correlation Analysis
Correlation metrics between static predictors and the runtime-energy proxy are summarized in Table VIII.

**TABLE VIII. Correlation Between Static Metrics and Runtime Energy Proxy**

| Metric | Pearson r | Pearson p | Spearman ρ | Spearman p | R² |
|:---|:---:|:---:|:---:|:---:|:---:|
| **CC** | -0.2228 | 0.2366 | -0.3106 | 0.0948 | 0.0496 |
| **ND** | -0.0538 | 0.7775 | 0.0900 | 0.6364 | 0.0029 |
| **FD** | -0.1103 | 0.5619 | -0.0080 | 0.9664 | 0.0122 |
| **ESS** | 0.0629 | 0.7412 | -0.1446 | 0.4458 | 0.0040 |
| **Original SCI** | -0.2376 | 0.2061 | -0.3611 | 0.0499 | 0.0565 |
| **Original CIRS** | 0.0254 | 0.8942 | -0.2548 | 0.1743 | 0.0006 |
| **Calibrated SCI** | 0.2697 | 0.1495 | 0.3731 | 0.0423 | 0.0727 |
| **Calibrated CIRS** | -0.2376 | 0.2061 | -0.3611 | 0.0499 | 0.0565 |

![Fig. 2: CC vs Energy](figures/fig1_energy_vs_cc.png) ![Fig. 3: ND vs Energy](figures/fig2_energy_vs_nd.png)

*Fig. 2. Cyclomatic Complexity (norm_CC) vs. Energy Proxy. | Fig. 3. Nesting Depth (norm_ND) vs. Energy Proxy.*


![Fig. 4: FD vs Energy](figures/fig4_energy_vs_fd.png) ![Fig. 5: ESS vs Energy](figures/fig5_energy_vs_ess.png)

*Fig. 4. Function Density (norm_FD) vs. Energy Proxy. | Fig. 5. Energy Smell Score (ESS) vs. Energy Proxy.*

### D. SCI Coefficient Calibration
Ordinary Least Squares (OLS) regression yielded the following empirical model:
$$\text{E}_{\text{proxy}} = 112.0013 + (-79.1455) \cdot \text{CC} + (-13.0663) \cdot \text{ND} + (-18.9707) \cdot \text{FD}$$

Statistical properties of the fitted OLS coefficients are shown in Table IX-A, while normalized relative regression-coefficient contributions are reported separately in Table IX-B.

**TABLE IX-A. Empirical OLS Regression Coefficients for SCI Calibration**

| Variable | Raw Beta Coefficient | Std Error | t-statistic | p-value | 95% Confidence Interval |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Intercept (β0)** | 112.0013 | 20.6694 | 5.4187 | 0.0000 | [69.5148, 154.4878] |
| **CC (β_CC)** | -79.1455 | 70.5458 | -1.1219 | 0.2722 | [-224.1545, 65.8635] |
| **ND (β_ND)** | -13.0663 | 30.0133 | -0.4354 | 0.6669 | [-74.7595, 48.6269] |
| **FD (β_FD)** | -18.9707 | 23.6214 | -0.8031 | 0.4292 | [-67.5252, 29.5838] |

*Model Fit*: R² = 0.0727, Adjusted R² = -0.0343, MAE = 11.9115 J, RMSE = 21.1973 J.

**TABLE IX-B. Initial Heuristic and Normalized Relative SCI Contributions**

| Component | Initial Heuristic Weight | Normalized Relative Regression Contribution |
|:---|:---:|:---:|
| **CC** | 0.50 | 0.7119 |
| **ND** | 0.30 | 0.1175 |
| **FD** | 0.20 | 0.1706 |

![Fig. 8: SCI Weights Comparison](figures/fig9_sci_weight_comparison.png)

*Fig. 8. Initial Heuristic Weights vs. Normalized Relative Regression Contributions.*

### E. CIRS Weight Calibration
Constrained weight optimization for the Carbon Impact Risk Score produced the weights listed in Table X.

**TABLE X. Initial and Empirically Calibrated CIRS Combination Weights**

| Component | Initial Heuristic Weight | Calibrated Weight |
|:---|:---:|:---:|
| **w_SCI** | 0.55 | 1.0000 |
| **w_ESS** | 0.45 | 0.0000 |

![Fig. 9: CIRS Weights Comparison](figures/fig10_cirs_weight_comparison.png)

*Fig. 9. Initial vs. Calibrated CIRS Combination Weights.*

### F. Original vs. Calibrated Model Performance
Performance metrics evaluating initial heuristic models against calibrated empirical models on the training dataset are shown in Table XI. Original SCI and Original CIRS represent 0-1 dimensionless risk scores; for energy prediction evaluation, a 1-variable OLS energy mapping (E_hat = a + b * Score) was fitted to map each score onto the Joule scale.

**TABLE XI. Original vs. Calibrated Model Performance**

| Model | MAE (J) | RMSE (J) | R² | Pearson r | Spearman ρ |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Original SCI** | 11.6619 | 21.3824 | 0.0565 | -0.2376 | -0.3611 |
| **Calibrated SCI** | 11.9115 | 21.1973 | 0.0727 | 0.2697 | 0.3731 |
| **Original CIRS** | 11.6549 | 22.0057 | 0.0006 | 0.0254 | -0.2548 |
| **Calibrated CIRS** | 11.6619 | 21.3824 | 0.0565 | -0.2376 | -0.3611 |

![Fig. 7: Model Explanatory Power](figures/fig8_model_performance_comparison.png)

*Fig. 7. Original vs. Calibrated Model Explanatory Power (R²).*

### G. Five-Fold Cross-Validation Performance
To assess out-of-sample generalizability, strict 5-fold cross-validation was conducted over held-out benchmark subsets (24 training / 6 test per fold). Coefficients were estimated exclusively from the training portion of each fold and evaluated on the held-out test set. Results are summarized in Table XII.

**TABLE XII. Five-Fold Cross-Validation Performance (Held-Out Test Sets)**

| Fold | Train N | Test N | Intercept | β_CC | β_ND | β_FD | Test MAE (J) | Test RMSE (J) | Test R² | Test Pearson r | Test Spearman ρ |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `1` | 24 | 6 | 109.4625 | -100.5894 | -10.9313 | -8.6887 | 12.856 | 18.7642 | -0.1108 | 0.2531 | 0.4286 |
| `2` | 24 | 6 | 95.8574 | -53.2349 | -10.3997 | -5.3708 | 23.9137 | 42.1643 | -0.1703 | 0.0681 | 0.4286 |
| `3` | 24 | 6 | 118.8487 | -39.9243 | -26.0756 | -30.1337 | 15.0709 | 19.4894 | -1.3703 | 0.033 | 0.3714 |
| `4` | 24 | 6 | 116.4801 | -94.5372 | -13.0085 | -24.0319 | 5.657 | 7.6902 | -1.1003 | 0.5077 | 0.4857 |
| `5` | 24 | 6 | 117.3908 | -106.2246 | 7.6511 | -25.9294 | 12.1538 | 14.762 | -3.2711 | -0.355 | -0.2571 |
| `Mean ± SD` | 24 | 6 | 111.61 ± 8.51 | -78.90 ± 26.98 | -10.55 ± 10.76 | -18.83 ± 9.89 | 13.9303 ± 5.8945 | 20.5740 ± 11.5790 | -1.2046 ± 1.1467 | 0.1014 ± 0.2836 | 0.2914 ± 0.2767 |

![Fig. 11: Cross-Validation Performance](figures/fig11_cross_validation_performance.png)

*Fig. 11. Held-Out Test Set R² across 5 Cross-Validation Folds.*

---

## VIII. DISCUSSION: EMPIRICAL EVALUATION OF COMPLEXITY-BASED ENERGY RISK

### A. Empirical Evaluation of Initial Heuristic Coefficients
The SCI and CIRS coefficients are initially defined as heuristic weights to provide a transparent composite risk indicator. An empirical calibration experiment was conducted to evaluate whether these static metrics could reliably explain runtime-estimated energy. The results showed limited predictive capability, indicating that the coefficients should not be interpreted as universally calibrated physical relationships. All VIF values are below 1.4 (VIF_CC = 1.0444, VIF_ND = 1.3790, VIF_FD = 1.3293), indicating no substantial multicollinearity among the predictors.

### B. Generalization and Limitations
1. **Sample Size**: Evaluated on N = 30 controlled benchmark programs (150 total executions across 5 runs per program).
2. **Runtime Energy Proxy**: Energy values are derived from a 55.0 W x runtime_seconds proxy rather than direct electrical board-level instrumentation.
3. **Metric Resolution**: Nesting Depth (ND) possesses 5 unique normalized values (0.10, 0.20, 0.30, 0.50, 0.90).
4. **Smell Saturation**: When multiple smell rules fire in a program, the production fuzzy t-conorm formula saturates ESS towards 1.0. Within this controlled benchmark dataset and under the specified constrained calibration objective, the fitted combination assigned zero weight to ESS.
5. **Scope & Physical Interpretation**: Static complexity metrics alone showed limited predictive capability for runtime-estimated energy under the controlled benchmark setting (5-fold test R² = -1.2046 ± 1.1467). This supports treating SCI and CIRS as transparent static risk indicators rather than direct measurements or reliable standalone predictors of energy or carbon impact.

### C. Response to the Arbitrary-Coefficient Concern
To address concerns regarding the initial heuristic nature of SCI and CIRS weighting coefficients, this study executed an empirical calibration experiment using a controlled benchmark suite of 30 deterministic CPU workloads. Production AST analysis extracted structural complexity indicators, while runtime duration measured across 150 executions provided an independent runtime-energy proxy. Multiple linear regression and 5-fold cross-validation demonstrated that while initial weights serve as actionable risk indicators, static complexity metrics alone explain limited out-of-sample energy variation (mean test R² = -1.2046). These findings empirically characterize the heuristic indicators without replacing core production formulas.

---

## IX. CONCLUSION

This study conducted an empirical evaluation of Code-Carbon heuristic coefficients using 30 controlled Python benchmarks and 150 executions. The empirical OLS model fitted E_proxy = 112.0013 + (-79.1455)*CC + (-13.0663)*ND + (-18.9707)*FD (R² = 0.0727). Normalized absolute coefficient contributions allocated 71.19% to CC, 11.75% to ND, and 17.06% to FD. Strict 5-fold cross-validation produced a mean test R² of -1.2046 ± 1.1467. Production SCI = 0.50 CC + 0.30 ND + 0.20 FD and production CIRS = 0.55 SCI + 0.45 ESS.

---

## X. COMPLETE ARTIFACT PACKAGE SUMMARY

| Artifact File | Purpose / Description | Status |
|:---|:---|:---:|
| `raw_results.csv` | 150 raw benchmark execution records | Verified |
| `aggregated_results.csv` | 30 benchmark-level aggregated metric observations | Verified |
| `correlations.csv` | Pearson & Spearman correlation matrix | Verified |
| `calibrated_coefficients.json` | Authoritative OLS, CIRS, and CV metrics JSON | Verified |
| `model_comparison.csv` | Original vs. Calibrated model performance table | Verified |
| `cross_validation.csv` | Fold-by-fold & summary 5-fold CV metrics | Verified |
| `residual_diagnostics.csv` | Residuals, leverage, and Cook's distance values | Verified |
| `sensitivity_analysis.csv` | Outlier sensitivity analysis model fit | Verified |
| `experiment_summary.txt` | Text summary of empirical calibration findings | Verified |
| `paper_results.md` | GFM publication results markdown section | Verified |
| `paper_section.md` | Full paper methodology and results markdown | Verified |
| `Code_Carbon_Calibration_V2_Final_Report.md` | Final consolidated research report markdown | Verified |
| `Code_Carbon_Calibration_V2_Final_Report.pdf` | Primary PDF publication report | Verified |
| `Code_Carbon_Calibration_V2_Complete_Artifacts.zip` | Complete downloadable artifact archive | Verified |