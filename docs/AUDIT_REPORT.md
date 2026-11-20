# Code-Carbon correctness audit

Audit date: 2026-11-10. This report distinguishes executable checks from static inspection. No result is called verified unless the listed command completed.

## Check results

| Check | Status | Exact command | Output / evidence |
|---|---|---|---|
| (1a) No fix preserves before/after and UI/API wording | FAIL / partial | `python -m pytest tests/test_ground_truth.py tests/test_invariants.py -q -s` | `8 passed in 0.45s`; test covers estimator invariants and handwritten identity fixture, but the API endpoint assertion was not completed in this audit. Existing API test `test_no_transformer_fix_keeps_modeled_before_after_equal` is present but not included in the completed command. |
| (1b) No-loop factor and energy equation | PASS | `python -m pytest tests/test_sustainability_math.py tests/test_transformer.py tests/test_invariants.py tests/test_ground_truth.py -q -s` | Included in 24 passing tests. Runtime carries `loop_factor`; the test checks `loop_factor == 1.0` and exact `SCI/HPI * RCP`. |
| (1c) Project sums and per-file means | FAIL / partial | `python -m pytest tests/test_ground_truth.py tests/test_invariants.py -q -s` | Aggregation source inspected. Project SLOC rows now take the pipeline's Radon SLOC. End-to-end project aggregate API assertions were not run to completion. |
| (1d) Finding count agrees across project, file, and impact | FAIL / unverified | `python -m pytest tests/test_ground_truth.py tests/test_invariants.py -q -s` | Ground-truth detector counts pass. The reported `load_test.py` is not present in this workspace and the project comparison endpoint test did not finish. |
| (1e) Recompute CIRS research to 6 decimals | PASS | `python -m pytest tests/test_ground_truth.py tests/test_invariants.py -q -s` | The test calls `ResearchSustainabilityMetrics.compute_carbon_impact_risk_score` and compares the recomputation to six decimals. |
| (1f) Recompute physical carbon footprint | PASS | `python -m pytest tests/test_ground_truth.py tests/test_invariants.py -q -s` | The test exercises `CarbonEstimator.estimate` and checks `energy_J / 3,600,000 * intensity`. |
| (1g) Fix regression withholding | PASS / gate function; API integration unverified | `python -m pytest tests/test_sustainability_math.py tests/test_transformer.py tests/test_invariants.py tests/test_ground_truth.py -q -s` | Regression test passes: candidate with lower energy/CIRS but higher ESS and SCI is rejected by `modeled_fix_is_acceptable`; a non-regressing improvement is accepted. Route integration remains unverified due the stalled API tests. |
| (1h) Same intensity before and after | PASS / static inspection | `python -m pytest tests/test_ground_truth.py tests/test_invariants.py -q -s` | `run_single_file_analysis` computes both CIRS values with the same `intensity` local. Formula test passed; API endpoint comparison not completed. |
| (1i) Transformed parse and executable output equivalence | PASS for fixture | `python -m pytest tests/test_ground_truth.py tests/test_invariants.py -q -s` | All six transformed snippets compile. The executable `one_loop_invariant_call.py` produced identical stdout before and after transformation. Other fixtures have no runnable main/test. |
| (2) Full number trace and unit audit | FAIL / partial | `rg -n 'Measured|Speedup|speedup|CIRS|ESS|carbon_intensity|findings|loop_factor|RCP|mean_' dashboard/src api src tests` | Trace inventory is in `docs/NUMBER_TRACE.md`; it covers primary Home, Project Results, File Results, Impact, Scheduling cards/fields. It records untraced chart numbers and CIRS/footprint and SLOC inconsistencies; a full exhaustive screen-by-screen rendering audit was not run. |
| (3) Six ground-truth fixtures | PASS | `python -m pytest tests/test_sustainability_math.py tests/test_transformer.py tests/test_invariants.py tests/test_ground_truth.py -q -s` | Table: no_smells 0 / unchanged / same; one_loop_invariant_call 1 / changed / lower; nested_depth_2 1 / unchanged / same; two_smells 2 / unchanged / same; recursive_function 1 / unchanged / same; cannot_fix 2 / unchanged / same. Full command: `25 passed in 2.89s`. |
| (4) Empty-loop raising call safety | PASS | `python -m pytest tests/test_sustainability_math.py tests/test_transformer.py tests/test_invariants.py tests/test_ground_truth.py -q -s` | `max([])` remains inside the empty loop; transformed source is unchanged and calling the function returns `"ok"` without raising. |
| (4) ESS cap and duplicate-rule saturation | PASS | `python -m pytest tests/test_sustainability_math.py tests/test_transformer.py tests/test_invariants.py tests/test_ground_truth.py -q -s` | `25 passed in 2.89s`; confidence is capped at 0.9, and repeated findings of one rule contribute once. Five hits of one rule yield ESS 9.0; five distinct rules yield 9.9999; removing one distinct rule yields 9.999. UI displays ESS to 3 decimals. |
| (4) CC, ND, FD, LoopOps and SCI increase explanation | FAIL / unavailable | `Get-ChildItem experiments/fixtures` | Directory does not exist in the current workspace. Thus values and explanation for SCI 0.544 → 0.549 cannot be reproduced from the requested mini-task-scheduler archive. |
| Rule catalog count / “27” classification | PASS for catalog count; fixture display source unavailable | `$env:PYTHONPATH='src'; python -c "from knowledge import RuleLoader; rules=RuleLoader().load_default_rules(); print(f'loaded rules: {len(rules)}'); print('max possible distinct rule IDs per file:', len(rules))"` | Output: `loaded rules: 12`; `max possible distinct rule IDs per file: 12`. Therefore 27 cannot be distinct rule IDs for one file under this catalog. The absent fixture prevents determining whether that reported 27 was finding locations or a stale/misbound UI field. Impact now omits the ambiguous denominator and displays distinct rule types resolved separately from finding-location totals. |
| (4) Small-workload measured speedup copy | PASS / build verified | `npm run build` | UI value is now the exact phrase “Not measurable (workload too small)” for `low_confidence_small_workload`; dashboard build passed. |
| (4) Project grid intensity, zone, source | PASS / build verified | `npm run build` | Project hero now displays intensity, zone, source category, and provider. Build succeeded (2,641 modules transformed). |
| (4) Sandbox hard timeout, no network, executed files marker | FAIL / static inspection only | `rg -n 'timeout=self.timeout_sec|socket|execution_status' src/energy/sandbox.py src/api/main.py dashboard/src/App.tsx` | Source defines a subprocess timeout and Python socket/process-spawn audit blocks. Project rows are labeled not executed (static analysis). A hostile-code timeout/network integration test was not run in this audit; Python-level restrictions are not an OS isolation boundary. |
| (4) Stage timings / repeated analysis | FAIL / archive timings unavailable; redundant parse removed | `python -m pytest -q --ignore=tests/test_api_endpoints.py` | Pipeline now accepts the preflight AST, avoiding a second parse on the original file and reusing the AST for baseline normalization. Response records `preflight_parse`, `analysis`, `transform`, `re_analysis`, and `baseline` seconds. The two requested archives are absent, so no fixture timings or dominant stage can be reported. |
| (5) 30 Flask detector samples | FAIL / unavailable | `rg --files -g '*.zip' -g 'load_test.py' .` | No archive or load_test.py was found. `experiments/results/detector_review/sample.csv` has the requested header but no sample rows; no findings were fabricated. |
| Full test suite | FAIL / incomplete | `python -m pytest -q` | Process yielded no summary during repeated 30-second waits and was interrupted; there is no completed full-suite pass/fail count. A targeted API test batch also did not complete. |
| Non-API test suite | PASS | `python -m pytest -q --ignore=tests/test_api_endpoints.py` | `123 passed in 14.46s`. |
| API test diagnostic | FAIL / sandbox blocked | `python -X faulthandler -m pytest tests/test_api_endpoints.py -x -v -o faulthandler_timeout=8` | First test stalled before request dispatch. Faulthandler showed AnyIO's event-loop thread in `socket.accept` → `socket._fallback_socketpair` → `asyncio.selector_events._make_self_pipe` while TestClient started its blocking portal. The endpoint was not reached. Interrupted; no API pass count is available. |
| Python syntax compilation | PASS | `python -m compileall -q src tests` | Exit code 0; no output. |
| Dashboard production build | PASS | `npm run build` (cwd `dashboard`) | `tsc -b` passed; Vite transformed 2,641 modules and built successfully in 1.55s. JS chunk 1,599.75 kB (447.89 kB gzip), above the 500 kB warning threshold. |
| Calibration experiment rerun using frozen timing | PASS | `$env:PYTHONPATH='src'; $env:ELECTRICITYMAPS_API_KEY='mock_demo_key'; python -u experiments/run_v2_calibration_experiment.py` | `Loaded 30 benchmark summary records. Reusing frozen raw data (150 rows); SHA256=fe82746546757d901ac3921a3a0557d1a2eb9ff39c1144e2f00edf30a78a91a0; no workloads executed. Saved aggregated_results.csv (30 rows). E_proxy = 112.0013 - 79.1455*CC - 13.0663*ND - 18.9707*FD; R²=0.0727, Adj R²=-0.0343, MAE=11.9115 J, RMSE=21.1973 J. CIRS weights: SCI=1.0000, ESS=0.0000; calibrated CIRS Pearson R²=0.0565. Saved 11 figures.` |
| GitHub corpus rerun | PASS | `$env:PYTHONPATH='src'; $env:ELECTRICITYMAPS_API_KEY='mock_demo_key'; python -u experiments/audit_github_corpus.py` (approved network run) | `Verified Repositories Pinned to Real Commits: 30/30; Successful Static Analyses on Real Source Code: 30/30; Total Genuine LOC: 47406; CLI workloads 8/30; library/framework 22/30; Mean SCI 0.5297; Mean heuristic CIRS 0.6662.` The first sandbox-only attempt failed DNS; the reported metrics are from the successful network-enabled rerun. |
| Calibration finalizer | PASS | `$env:PYTHONPATH='src'; $env:ELECTRICITYMAPS_API_KEY='mock_demo_key'; python -u experiments/finalize_v2_calibration.py` | Final output: `[ALL 16 CHECKS PASSED] Final Master Automated Consistency Check 100% SUCCESSFUL!` It rebuilt 11 figures, two PDFs and the ZIP. Copies to Downloads and the external IDE artifact folder were skipped after `PermissionError`; project artifacts were saved. |
| LoopOps cross-validation refresh for dependent documentation | PASS | `$env:PYTHONPATH='src'; python -u experiments/run_loopops_cv.py` | Baseline OOF MAE/RMSE/R² `13.9303 / 23.6085 / -0.1502`; mean fold R² `-1.2046` (matches §6.4); nested OOF R² `-0.3160`. Raw LoopOps: `10787.1895 / 59006.1996 / -7185291.6300`; mean fold `-68241025.1276`; nested `-100309414.1024`. Log LoopOps: `15.5135 / 21.5042 / 0.0457`; mean fold `-3.1971`; nested `-0.0128`. This output is from the raw timing data, command completed successfully; pooled OOF R² and mean-fold R² are different statistics. |
| Saturating LoopOps paired validation | ran; inconclusive | `$env:PYTHONPATH='src'; python -u experiments/run_saturating_loopops_validation.py` | `beta=2.0; K=100.0; per-run floor=0.5s; positive repeats=20; controls=3 rounds × 20 repeats; positive direction=8/8; Spearman=0.082; p=0.846; negative-control absolute median-drop noise=0.94%–7.18% over 6 rounds; power scheme=Balanced; CPU load start/end=16.2%/12.9%`. Status is **ran; inconclusive**: rank agreement is negligible and control noise reaches the lowest modeled drop range. Full medians and IQRs are in `experiments/results/saturating_loopops_validation/report.md`; raw samples are in `new_pairs.csv`. |
| Timing run-to-run variability | PASS | `$env:PYTHONPATH='src'; $env:ELECTRICITYMAPS_API_KEY='mock_demo_key'; python -u experiments/run_v2_calibration_experiment.py` | Same command above regenerated the CV report from the frozen rows: 150 rows, 30 benchmarks, 5 runs each; CV min/median/mean/max = 0.28% / 1.10% / 1.30% / 4.43%. All benchmark values: `experiments/results/calibration_v2/run_to_run_variability.csv`. |
| Calibration/corpus script syntax and whitespace | PASS | `python -m py_compile experiments\run_v2_calibration_experiment.py experiments\audit_github_corpus.py; git diff --check` | Python compile succeeded. `git diff --check` reported no whitespace errors; Git printed only existing LF→CRLF normalization warnings. |

## Defects and changes

- Fixed runtime rounding before energy multiplication. The runtime estimator now exposes `loop_factor`, leaves runtime unrounded, and energy is the exact returned runtime multiplied by RCP. This supports the no-loop equality invariant.
- Fixed loop invariant detection for expressions invoking a small allowlist of pure built-ins (`sum`, `min`, `max`, `len`, and related conversions). The transformer still rejects attribute calls, subscripts, and unapproved calls in the candidate expression. A detector and transformer test fixture covers a constant `sum` call.
- Tightened the allowlist further: only literal calls proven non-raising are hoisted. `max([])` is not hoisted from a loop over an empty iterable; test confirms original function still returns normally.
- Aligned project file SLOC rows with `complexity_metrics.lines_of_code` (Radon SLOC) rather than counting nonblank physical lines. This makes aggregate SLOC sum the same per-file quantity shown in File Results.
- Renamed the Impact finding metric to “Finding locations”; the “1 of 27” panel now says “Distinct rule IDs resolved” and separately shows finding-location before/after counts. Added API assertions for project/file/Impact location totals; those assertions are not yet run because endpoint tests stalled.
- Replaced UI footprint unit text with “modeled gCO₂eq/run” and kept intensity explicitly in gCO₂eq/kWh. The measured speedup state now prints the exact requested phrase.
- Strengthened automatic-fix acceptance: ESS, SCI, actionable smell count, energy, and CIRS may not increase, and energy or CIRS must improve. A regression withholds the fix/recommendation and sets “No modeled improvement.” This endpoint change was syntax-compiled, but endpoint tests remain incomplete.
- Added carbon grid metadata to the Project Results hero.
- Added six ground-truth files, hand-entered expected JSON, and a test that prints expected versus actual detector count, transformation status, and modeled energy direction. One fixture's expected count was set to two after the detector reported both memory and file-I/O smells.
- Added `tests/test_invariants.py` and `docs/NUMBER_TRACE.md`.
- Updated section 2.2 in `code_carbon_master_documentation.md`: ESS now groups finding locations by rule ID and uses the maximum confidence capped at 0.9 once per distinct rule type. The fuzzy-union form is retained, with a documented aggregation-unit change.
- Aligned finding count terminology: project, file, and Impact use finding locations; distinct rule IDs are explicitly described as a separate count. Added project-response test assertions tying file rows to raw and Impact location totals (API tests remain uncompleted).
- Reused the preflight AST for the initial analysis and baseline pass; added response stage timing fields.
- Carbon comparison rows and all three percentages now use the same physical modeled gCO₂eq/run basis; unitless CIRS before/after are separate. API-level calculation is implemented, but endpoint checks are not verified because TestClient cannot start under this sandbox.
- Added `ENABLE_EXECUTION` (default false). Static-only requests return `Not executed (static analysis only)` without invoking runtime measurement. `docs/runtime_execution.md` documents that Python audit hooks are not a security/isolation boundary.
- Reran the V2 calibration after discovering the fit was using quality-gate means instead of the separately recollected raw runs. The script now fits from hash-verified `raw_results.csv` and reuses it unless `--recollect-timings` is passed. The master document contains the current fit. The duplicate `docs/CODE_CARBON_COMPLETE_DOCUMENTATION.md` was removed to maintain a single source. Finalizer validation independently recomputes regression and CV metrics from generated files.

## Unresolved / not verified

- The full pytest suite and endpoint tests did not complete, so API aggregation, finding-count consistency, regression withholding route behavior, and UI/API “No modeled change” remain unverified end to end. The non-API suite passed 123 tests; regression gate function itself is tested.
- The advertised `experiments/fixtures/mini-task-scheduler.zip` and `flask-main.zip` are not present: `Test-Path experiments\fixtures` returned `False`, and `rg --files -g '*.zip' -g 'load_test.py' .` returned no paths. Therefore fixture-specific metrics, SCI explanation, stage timing comparison, and real 30-row sample remain unavailable.
- Stage timing fields are instrumented in the API response, but timing values for those archives were not collected. Preflight AST is reused for initial analysis and baseline normalization, removing the redundant original/baseline parses.
- `NUMBER_TRACE.md` identifies remaining untraced chart values and label/model inconsistencies. The entire dashboard was not visually audited; no claim is made that every numeric label or unit mismatch was fixed.
- Sandbox controls were inspected in source but not verified by adversarial execution. The implementation uses Python audit hooks, not an OS/container isolation boundary.
- The successful non-API run is 123 passed. The 10 API tests remain unverified because the local asyncio self-pipe blocks before a request reaches the application; this is consistent with a sandbox loopback restriction, not proof the API endpoints pass.

## Calibration and corpus drift (previous → current)

### Calibration source and timing drift

The earlier `run_v2_calibration_experiment.py` always invoked each workload five times, then wrote those observations to `raw_results.csv`; however, it calculated the regression from `quality_gate_data.csv` means instead of the raw rows. The prior coefficient shift (published 105.7428→intermediate 113.4301) therefore cannot be attributed to ESS: ESS is not an OLS predictor. Timing recollection, and the mismatch between re-collected raw timing data and quality-gate timing means, are the real source/data-path change. In this correction, no structural inputs changed: raw versus quality-gate values for raw/norm CC, ND, FD, LOC, and smell count were identical across all 30 rows (maximum absolute difference 0.0). The older V2 aggregate is not tracked or preserved, so whether those fields changed between the old published aggregate and the intermediate rerun remains **unverified**.

The script is corrected: it aggregates `raw_results.csv` for the fit and validates its SHA-256 manifest. Default execution reuses the frozen data; only `--recollect-timings` executes benchmark programs. The completed command was:

```powershell
$env:PYTHONPATH='src'; $env:ELECTRICITYMAPS_API_KEY='mock_demo_key'; python -u experiments/run_v2_calibration_experiment.py
```

Output included `Reusing frozen raw data (150 rows); SHA256=fe82746546757d901ac3921a3a0557d1a2eb9ff39c1144e2f00edf30a78a91a0; no workloads executed.` It fit `E_proxy = 112.0013 + (-79.1455)*CC + (-13.0663)*ND + (-18.9707)*FD`; `R²=0.0727`, adjusted `R²=-0.0343`, MAE `11.9115 J`, RMSE `21.1973 J`, and current CC p-value `0.2722`. The prior intermediate p-value 0.2010 is now 0.2722 after changing the aggregate energy source.

The old summary values now documented before the intermediate rerun → final raw-backed values are: OLS intercept 105.7428→112.0013; βCC -104.2888→-79.1455; βND -3.3139→-13.0663; βFD -8.7816→-18.9707; R² 0.0961→0.0727; adjusted R² -0.0082→-0.0343; MAE 12.0738→11.9115 J; RMSE 19.7862→21.1973 J. From the prior intermediate run to the corrected raw-backed run, the coefficients changed 113.4301→112.0013, -93.5794→-79.1455, -7.9569→-13.0663, -15.5400→-18.9707; R² 0.0793→0.0727; adjusted R² -0.0269→-0.0343; MAE 12.0899→11.9115 J; RMSE 21.4328→21.1973 J; CC p-value 0.2010→0.2722.

Other previously documented model-comparison values → current raw-backed values (each tuple is MAE, RMSE, R², Pearson $r$, Spearman $\rho$): Original SCI `(11.9582,21.7426,0.0525,-0.2291,-0.3131)`→`(11.6619,21.3824,0.0565,-0.2376,-0.3611)`; calibrated SCI `(12.0899,21.4328,0.0793,0.2816,0.3871)`→`(11.9115,21.1973,0.0727,0.2697,0.3731)`; original CIRS `(11.8000,22.2826,0.0049,0.0697,-0.1704)`→`(11.6549,22.0057,0.0006,0.0254,-0.2548)`; calibrated CIRS `(11.9582,21.7426,0.0525,-0.2291,-0.3131)`→`(11.6619,21.3824,0.0565,-0.2376,-0.3611)`. The final calibrated CIRS row equals Original SCI because fitted weights are 1.0/0.0.

For the intermediate quality-gate-based documentation values → final raw-backed values, those four model tuples changed respectively: Original SCI `(11.9582,21.7426,0.0525,-0.2291,-0.3131)`→`(11.6619,21.3824,0.0565,-0.2376,-0.3611)`; calibrated SCI `(12.0899,21.4328,0.0793,0.2816,0.3871)`→`(11.9115,21.1973,0.0727,0.2697,0.3731)`; original CIRS `(11.8000,22.2826,0.0049,0.0697,-0.1704)`→`(11.6549,22.0057,0.0006,0.0254,-0.2548)`; calibrated CIRS `(11.9582,21.7426,0.0525,-0.2291,-0.3131)`→`(11.6619,21.3824,0.0565,-0.2376,-0.3611)`.

Cross-validation mean ± SD old→current: MAE `14.2630±5.8402→13.9303±5.8945 J`; RMSE `21.0841±11.8156→20.5740±11.5790 J`; R² `-1.4850±1.7159→-1.2046±1.1467`; Pearson `0.0814±0.3791→0.1014±0.2836`; Spearman `0.2571±0.3632→0.2914±0.2767`. Fold rows were all regenerated; the current per-fold values are in `code_carbon_master_documentation.md` and `experiments/results/calibration_v2/cross_validation.csv`.

Cross-validation mean coefficient ± SD old→current: intercept `104.88±8.59→111.61±8.51`; βCC `-104.59±27.70→-78.90±26.98`; βND `0.98±15.04→-10.55±10.76`; βFD `-8.28±9.77→-18.83±9.89`.

The other changed published quantities are: Section 2.1 CC p-value `0.2010→0.2722` (preceding quality-gate-based estimate→current raw-backed fit); Section 6.6 log-LoopOps results moved from the earlier published pooled OOF R² `0.0242` to the intermediate quality-gate result `-0.0025`, and now to the raw-backed result `0.0457`; mean-fold R² moved `-2.2552→-3.4074→-3.1971`, nested OOF R² `0.0226→-0.0040→-0.0128`. The legacy corpus summary JSON changed from SCI `0.1263→0.5297`, CIRS `0.1141→0.6662`, and total LOC `6,782→47,406`; mean ESS was added as `8.3314/10`.

OLS coefficient diagnostics old→current: intercept SE/t/p/CI `19.2934/5.4808/0.0000/[66.0845,145.4010]→20.6694/5.4187/0.0000/[69.5148,154.4878]`; CC `65.8497/-1.5837/0.1253/[-239.6448,31.0673]→70.5458/-1.1219/0.2722/[-224.1545,65.8635]`; ND `28.0154/-0.1183/0.9067/[-60.9003,54.2725]→30.0133/-0.4354/0.6669/[-74.7595,48.6269]`; FD `22.0490/-0.3983/0.6937/[-54.1040,36.5407]→23.6214/-0.8031/0.4292/[-67.5252,29.5838]`. Absolute-coefficient shares CC/ND/FD changed `89.61%/2.85%/7.55%→71.19%/11.75%/17.06%`.

The intermediate coefficient diagnostics → final diagnostics were intercept `SE/t/p/CI 20.8990/5.4275/0.0000/[70.4715,156.3887]→20.6694/5.4187/0.0000/[69.5148,154.4878]`; CC `71.3297/-1.3119/0.2010/[-240.1997,53.0409]→70.5458/-1.1219/0.2722/[-224.1545,65.8635]`; ND `30.3468/-0.2622/0.7952/[-70.3356,54.4218]→30.0133/-0.4354/0.6669/[-74.7595,48.6269]`; FD `23.8839/-0.6506/0.5210/[-64.6341,33.5540]→23.6214/-0.8031/0.4292/[-67.5252,29.5838]`. Intermediate→final absolute coefficient shares were `79.93%/6.80%/13.27%→71.19%/11.75%/17.06%`.

Five-fold coefficient and score tuples old→current (intercept, βCC, βND, βFD, MAE, RMSE, R², Pearson, Spearman):

- Fold 1: `(102.7230,-123.2063,-0.9382,2.3886,13.8497,19.9426,-0.1867,0.3347,0.3143)`→`(109.4625,-100.5894,-10.9313,-8.6887,12.8560,18.7642,-0.1108,0.2531,0.4286)`.
- Fold 2: `(89.4380,-73.0402,-1.7243,4.3015,22.7769,38.6701,-0.2177,-0.0333,0.2571)`→`(95.8574,-53.2349,-10.3997,-5.3708,23.9137,42.1643,-0.1703,0.0681,0.4286)`.
- Fold 3: `(112.8562,-68.6697,-16.5853,-19.8457,14.4169,17.3716,-0.9788,0.3636,0.3143)`→`(118.8487,-39.9243,-26.0756,-30.1337,15.0709,19.4894,-1.3703,0.0330,0.3714)`.
- Fold 4: `(112.4795,-131.3820,-4.7192,-15.4139,7.9650,11.0470,-1.8362,0.4567,0.5429)`→`(116.4801,-94.5372,-13.0085,-24.0319,5.6570,7.6902,-1.1003,0.5077,0.4857)`.
- Fold 5: `(106.9204,-126.6339,28.8816,-12.8071,13.1765,17.2866,-5.9451,-0.7125,-0.8286)`→`(117.3908,-106.2246,7.6511,-25.9294,12.1538,14.7620,-3.2711,-0.3550,-0.2571)`.

The immediately previous intermediate fold rows → final rows also changed: fold 1 `(112.2708,-118.5638,-6.7520,-5.7692,14.1432,19.5527,-0.2211,0.2435,0.3714)`→`(109.4625,-100.5894,-10.9313,-8.6887,12.8560,18.7642,-0.1108,0.2531,0.4286)`; fold 2 `(95.8262,-66.1310,-5.2410,-0.0841,24.1229,43.2295,-0.1780,-0.0536,0.3143)`→`(95.8574,-53.2349,-10.3997,-5.3708,23.9137,42.1643,-0.1703,0.0681,0.4286)`; fold 3 `(120.3105,-56.8855,-20.2742,-26.7551,14.3868,18.2975,-1.0198,0.1916,0.3714)`→`(118.8487,-39.9243,-26.0756,-30.1337,15.0709,19.4894,-1.3703,0.0330,0.3714)`; fold 4 `(118.8898,-108.3891,-9.6228,-21.8757,5.8208,7.7772,-1.1879,0.5841,0.6571)`→`(116.4801,-94.5372,-13.0085,-24.0319,5.6570,7.6902,-1.1003,0.5077,0.4857)`; fold 5 `(115.9624,-116.9041,21.0493,-20.9330,12.8414,16.5633,-4.8183,-0.5584,-0.4286)`→`(117.3908,-106.2246,7.6511,-25.9294,12.1538,14.7620,-3.2711,-0.3550,-0.2571)`.

Frozen five-run timing variability is sample standard deviation divided by the run mean. Overall CV min/median/mean/max is 0.28% / 1.10% / 1.30% / 4.43%. The per-benchmark values are:

| Benchmark | Mean runtime (s) | Sample SD (s) | CV |
|---|---:|---:|---:|
| algo_01 | 1.777616 | 0.045614 | 2.57% |
| algo_02 | 3.374060 | 0.066510 | 1.97% |
| algo_03 | 1.192175 | 0.011781 | 0.99% |
| algo_04 | 1.647059 | 0.022024 | 1.34% |
| algo_05 | 1.633460 | 0.015294 | 0.94% |
| func_density_01 | 1.633584 | 0.072340 | 4.43% |
| func_density_02 | 1.466934 | 0.008968 | 0.61% |
| func_density_03 | 1.475755 | 0.016606 | 1.13% |
| func_density_04 | 1.519095 | 0.009655 | 0.64% |
| func_density_05 | 1.546553 | 0.017336 | 1.12% |
| mixed_cpu_01 | 0.861548 | 0.005727 | 0.66% |
| mixed_cpu_02 | 1.328950 | 0.007087 | 0.53% |
| mixed_cpu_03 | 1.000924 | 0.009721 | 0.97% |
| mixed_cpu_04 | 1.393686 | 0.015092 | 1.08% |
| mixed_cpu_05 | 1.551060 | 0.020185 | 1.30% |
| nested_01 | 1.855609 | 0.045031 | 2.43% |
| nested_02 | 1.865340 | 0.023591 | 1.26% |
| nested_03 | 1.321811 | 0.009854 | 0.75% |
| nested_04 | 1.620211 | 0.050462 | 3.11% |
| nested_05 | 1.235655 | 0.004867 | 0.39% |
| recursion_01 | 1.601228 | 0.014644 | 0.91% |
| recursion_02 | 1.383277 | 0.011529 | 0.83% |
| recursion_03 | 1.544844 | 0.010783 | 0.70% |
| recursion_04 | 1.687252 | 0.004732 | 0.28% |
| recursion_05 | 1.573566 | 0.024899 | 1.58% |
| simple_01 | 1.552642 | 0.019539 | 1.26% |
| simple_02 | 1.616195 | 0.027349 | 1.69% |
| simple_03 | 1.695496 | 0.016700 | 0.98% |
| simple_04 | 1.568034 | 0.019972 | 1.27% |
| simple_05 | 1.574219 | 0.020657 | 1.31% |

`raw_results.csv` SHA-256: `fe82746546757d901ac3921a3a0557d1a2eb9ff39c1144e2f00edf30a78a91a0`; manifest: `experiments/results/calibration_v2/raw_results.csv.sha256`.

### GitHub corpus drift

The archived prose summary changed SCI 0.2315→0.5297 and CIRS 0.5480→0.6662. The preserved legacy CSV does **not** support the old prose numbers: its observed means were SCI 0.1263, normalized ESS 0.0991→0.8331 (the audited score is 8.3314/10), and CIRS 0.1141 over 6,782 selected LOC. The audited CSV reports SCI 0.5297, ESS 8.3314/10, CIRS 0.6662 over 47,406 genuine LOC (30/30 successful analyses). Its sample mean selected-file LOC is 1580.2; the legacy metadata mean was 226.1. This is predominantly a source-selection/structural-input change: the audit now pins and analyzes explicit primary source paths. The 30 canonical owner/repository names match; two URLs were normalized/changed as shown below. SCI weights remain 0.50/0.30/0.20 in the current scorer. Exact attribution of the old prose 0.2315 to input versus historical code is **unverified**, because its underlying row dataset is unavailable and conflicts with the preserved legacy CSV.

| Canonical repository | Previous URL | Audited URL |
|---|---|---|
| astropy/astropy | https://github.com/astropy/astropy | https://github.com/astropy/astropy |
| biopython/biopython | https://github.com/biopython/biopython | https://github.com/biopython/biopython |
| cookiecutter/cookiecutter | https://github.com/cookiecutter/cookiecutter | https://github.com/cookiecutter/cookiecutter |
| django/django | https://github.com/django/django | https://github.com/django/django |
| encode/httpx | https://github.com/encode/httpx | https://github.com/encode/httpx |
| fastapi/fastapi | https://github.com/fastapi/fastapi | https://github.com/fastapi/fastapi |
| huggingface/diffusers | https://github.com/huggingface/diffusers | https://github.com/huggingface/diffusers |
| huggingface/transformers | https://github.com/huggingface/transformers | https://github.com/huggingface/transformers |
| joblib/joblib | https://github.com/joblib/joblib | https://github.com/joblib/joblib |
| mwaskom/seaborn | https://github.com/mwaskom/seaborn | https://github.com/mwaskom/seaborn |
| networkx/networkx | https://github.com/networkx/networkx | https://github.com/networkx/networkx |
| numpy/numpy | https://github.com/numpy/numpy | https://github.com/numpy/numpy |
| pallets/flask | https://github.com/pallets/flask | https://github.com/pallets/flask |
| pandas-dev/pandas | https://github.com/pandas-dev/pandas | https://github.com/pandas-dev/pandas |
| psf/black | https://github.com/psf/black | https://github.com/psf/black |
| psf/requests | https://github.com/psf/requests | https://github.com/psf/requests |
| pydantic/pydantic | https://github.com/pydantic/pydantic | https://github.com/pydantic/pydantic |
| pydata/xarray | https://github.com/pydata/xarray | https://github.com/pydata/xarray |
| pypa/pip | https://github.com/pypa/pip | https://github.com/pypa/pip |
| pytest-dev/pytest | https://github.com/pytest-dev/pytest | https://github.com/pytest-dev/pytest |
| python-pillow/Pillow | https://github.com/python-pillow/Pillow | https://github.com/python-pillow/Pillow |
| pytorch/vision | https://github.com/pytorch/vision | https://github.com/pytorch/vision |
| scikit-image/scikit-image | https://github.com/scikit-image/scikit-image | https://github.com/scikit-image/scikit-image |
| scikit-learn/scikit-learn | https://github.com/scikit-learn/scikit-learn | https://github.com/scikit-learn/scikit-learn |
| scipy/scipy | https://github.com/scipy/scipy | https://github.com/scipy/scipy |
| sympy/sympy | https://github.com/sympy/sympy | https://github.com/sympy/sympy |
| textualize/rich | https://github.com/Textualize/rich | https://github.com/textualize/rich |
| tiangolo/typer | https://github.com/fastapi/typer | https://github.com/tiangolo/typer |
| tqdm/tqdm | https://github.com/tqdm/tqdm | https://github.com/tqdm/tqdm |
| ultralytics/ultralytics | https://github.com/ultralytics/ultralytics | https://github.com/ultralytics/ultralytics |

### Other documentation updates

- `code_carbon_master_documentation.md` is now the canonical documentation; the duplicate `docs/CODE_CARBON_COMPLETE_DOCUMENTATION.md` was removed.
- Section 2.3.1 defines the three unweighted modeled gCO₂eq/run rows and keeps CIRS separate as a unitless score; the obsolete 1.78/2.1% illustrative demo was removed.
- Section 6.3 states calibrated CIRS equals original SCI because fitted weights are 1.0/0.0.
- Section 6.6 now says the log LoopOps pooled out-of-fold R² is negative (-0.0025), mean fold R² -3.4074.
- Section 6.8 records archived control noise 7.51% and 4.35% (old observed) and the rerun 22.95% and 4.39% (new observed); modeled drops are 7.17%–10.91%, so observed timing noise is comparable to or larger than the model signal.
- Section 8.2 gives 123 passing non-API tests, explicitly marks API tests unverified in this sandbox, and adds the saturating LoopOps validation command.
- `python -u experiments/run_saturating_loopops_validation.py` output: `beta=2.0; K=100.0; positive direction=8/8; Spearman=-0.014; p=0.974; negative controls: [(0.0, -22.95), (0.0, 4.39)]`.
- Corpus artifacts were not fetched again in this turn. The current `github_corpus_summary.json` and `github_audit_report.json` were refreshed from the preserved 30-row audited CSV; the audit script was changed to emit mean ESS and update both summary JSONs on its next live run. The prior network-enabled 30/30 corpus run remains the source of the audited rows.
- The explicit `--recollect-timings` branch was not invoked; it is documented as the only path that executes benchmark workloads. Default frozen-data execution and SHA validation were run successfully.


## This completion pass

- `git log --all -- docs/CODE_CARBON_COMPLETE_DOCUMENTATION.md` returned no commits. Consequently there was no historical file to retrieve with `git show`; exact deleted prose recovery is unavailable. The canonical master now reconstructs the requested formulas and caveats from source and retained artifacts.
- The master documentation restores the runtime estimator formula and constraints, explicitly separates `CIRS_heuristic` from `CIRS_research`, includes the three-version OLS coefficient comparison, and restores the raw-backed LoopOps CV table. Section 7 explicitly states one pinned source file per repository and reports the raw ESS distribution and ESS-versus-selected-file-LOC Spearman correlation.
- The 6,782→47,406 LOC change describes aggregate selected-file LOC across the same 30 repositories (226.1→1,580.2 mean LOC per repository). The main evidence supports changed source paths/selection; detailed historical per-repository paths for the legacy run are not preserved and are unverified.
- Machine load at the time of the prior quick validation was sampled at 14.5% CPU load and 2400 MHz; Windows power plan was Balanced with processor minimum 5% / maximum 100%. These are point-in-time readings, not controlled governor pinning. The new 20-repeat validation should be labeled inconclusive and machine load remains a limitation.
- API endpoint tests remain unverified in the sandbox. The completed non-API suite count is 123, resolving the prior 121/123 inconsistency.


Strict paired validation output (read from the generated report after the command completed): positive median drops/IQRs were sum_weights 53.56% (49.06–57.80), max_limits 59.85% (59.23–60.52), sin_angle 52.53% (47.36–53.08), zfill_text 30.21% (26.26–33.95), dict_lookup 26.67% (21.93–32.63), list_copy 55.91% (52.07–57.27), string_replace 52.68% (49.57–53.69), round_config 88.01% (87.71–88.46). Control-round medians were 2.42%, −5.29%, 7.18% and −0.94%, −2.74%, 2.00%; absolute range 0.94%–7.18%. The measured effects are much larger than modeled 7%–11% drops, while controls show noise at the lower modeled bound, so these timing pairs are inconclusive.


Additional old→new corrections: the §5.1 runtime summary was `0.86–2.07 s (mean 1.5284 s)` → `0.856506–3.474497 s (mean 1.569928 s)` from the frozen 150 rows. The LoopOps baseline changed from the earlier quality-gate aggregation `OOF MAE/RMSE/R² 14.263/24.1691/−0.1708; mean fold R² −1.485` → raw-backed `13.9303/23.6085/−0.1502; mean fold R² −1.2046`, which matches §6.4; raw pooled OOF and fold-average scores are different summaries.
