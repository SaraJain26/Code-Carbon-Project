# Saturating LoopOps validation on new pairs

Each measured invocation was scaled to at least 0.5s. Positive pairs use 20 repeats per version and report the median plus the interquartile range (IQR) of paired percentage drops. Each negative control was independently rerun 3 times, with 20 repeats per version in each round. Constants were fixed in advance; all pairs preserve return values and use identical before/after inputs and iteration counts.

Configured constants: **beta=2.0, K=100.0**.
Positive-pair direction agreement: **8/8**; Spearman rho: **0.082** (p=0.846, n=8).
Negative-control modeled drops were zero. Absolute control median-drop noise range across all 6 rounds: **0.94%–7.18%**.
Machine check: platform `Windows-11-10.0.26200-SP0`; power scheme `Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Balanced)`; CPU frequency `1520 MHz`; CPU load sample at start/end `16.2%` / `12.9%`. CPU load was sampled at run boundaries, not continuously during every pair.

## Positive hoists

| Pair | Work type | Ops before → after | Modeled drop | Measured drop median (IQR) |
|---|---|---:|---:|---:|
| sum_weights | sum call | 50.0 → 32.0 | 10.91% | 53.56% (49.06–57.80) |
| max_limits | max call | 50.0 → 32.0 | 10.91% | 59.85% (59.23–60.52) |
| sin_angle | math.sin | 50.0 → 32.0 | 10.91% | 52.53% (47.36–53.08) |
| zfill_text | string method | 70.0 → 52.0 | 7.64% | 30.21% (26.26–33.95) |
| dict_lookup | dict get call | 50.0 → 32.0 | 10.91% | 26.67% (21.93–32.63) |
| list_copy | list allocation call | 74.0 → 56.0 | 7.17% | 55.91% (52.07–57.27) |
| string_replace | string replace | 70.0 → 52.0 | 7.64% | 52.68% (49.57–53.69) |
| round_config | round call | 50.0 → 32.0 | 10.91% | 88.01% (87.71–88.46) |

## Negative controls

| Negative control | Round | Measured drop median (IQR) |
|---|---:|---:|
| constant_arithmetic_control | 1 | 2.42% (0.66–5.33) |
| constant_arithmetic_control | 2 | -5.29% (-10.90–-1.31) |
| constant_arithmetic_control | 3 | 7.18% (1.39–10.02) |
| noop_rewrite_control | 1 | -0.94% (-4.41–0.95) |
| noop_rewrite_control | 2 | -2.74% (-5.90–1.23) |
| noop_rewrite_control | 3 | 2.00% (0.09–7.80) |

This small hand-built validation is exploratory, not broad calibration. It does not establish physical energy accuracy or general runtime prediction.
