"""Compare the existing 3-predictor CV model with a LoopOps 4th predictor.

Aggregates the frozen five-run ``raw_results.csv`` and uses the same
category-stratified 5-fold assignments as the V2 calibration. The baseline
must match §6.4; no workloads are executed by this analysis.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from energy.loop_ops import loop_weighted_ops  # noqa: E402

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "loopops_cv"
INPUT_CSV = PROJECT_ROOT / "experiments" / "results" / "calibration_v2" / "raw_results.csv"
BENCHMARK_DIR = PROJECT_ROOT / "experiments" / "benchmarks_v2"


def fit_predict(train_x: np.ndarray, train_y: np.ndarray, test_x: np.ndarray) -> np.ndarray:
    """Fit OLS after train-only standardization for numeric stability."""
    means = train_x.mean(axis=0)
    scales = train_x.std(axis=0)
    scales[scales == 0] = 1.0
    train_z = (train_x - means) / scales
    test_z = (test_x - means) / scales
    train_design = np.column_stack([np.ones(len(train_z)), train_z])
    test_design = np.column_stack([np.ones(len(test_z)), test_z])
    beta, *_ = np.linalg.lstsq(train_design, train_y, rcond=None)
    return test_design @ beta


def metrics(actual: np.ndarray, predicted: np.ndarray) -> tuple[float, float, float]:
    errors = actual - predicted
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))
    total = float(np.sum((actual - actual.mean()) ** 2))
    r2 = 1.0 - float(np.sum(errors**2)) / total if total else 0.0
    return mae, rmse, r2


def main() -> None:
    raw = pd.read_csv(INPUT_CSV)
    df = raw.groupby(["benchmark_id", "category"], sort=False).agg(
        LOC=("LOC", "first"),
        norm_CC=("norm_CC", "first"),
        norm_ND=("norm_ND", "first"),
        norm_FD=("norm_FD", "first"),
        runtime_energy_proxy_j=("runtime_energy_proxy_j", "mean"),
    ).reset_index()
    if len(raw) != len(df) * 5 or not raw["success"].astype(bool).all():
        raise ValueError("Expected exactly five successful frozen raw runs per benchmark.")
    loop_ops = []
    for row in df.itertuples(index=False):
        path = BENCHMARK_DIR / row.category / f"{row.benchmark_id}.py"
        loop_ops.append(loop_weighted_ops(path.read_text(encoding="utf-8")))
    df["LoopOps"] = loop_ops

    y = df["runtime_energy_proxy_j"].to_numpy(dtype=float)
    base_x = df[["norm_CC", "norm_ND", "norm_FD"]].to_numpy(dtype=float)
    raw_extended_x = df[["norm_CC", "norm_ND", "norm_FD", "LoopOps"]].to_numpy(dtype=float)
    log_extended_x = np.column_stack([
        base_x,
        np.log10(1.0 + df["LoopOps"].to_numpy(dtype=float)),
    ])

    folds: list[list[int]] = [[] for _ in range(5)]
    for _, group in df.groupby("category"):
        for fold_index, row_index in enumerate(group.index.tolist()):
            folds[fold_index % 5].append(row_index)

    model_features = {
        "baseline": base_x,
        "with_raw_loopops": raw_extended_x,
        "with_log_loopops": log_extended_x,
    }
    predictions = {name: np.zeros(len(df)) for name in model_features}
    fold_rows: list[dict[str, object]] = []
    for fold_index, test_indices in enumerate(folds):
        test_idx = np.array(test_indices, dtype=int)
        train_idx = np.array([i for i in range(len(df)) if i not in test_indices], dtype=int)
        for model_name, features in model_features.items():
            predicted = fit_predict(features[train_idx], y[train_idx], features[test_idx])
            predictions[model_name][test_idx] = predicted
            mae, rmse, r2 = metrics(y[test_idx], predicted)
            fold_rows.append({
                "fold": fold_index + 1,
                "model": model_name,
                "train_n": len(train_idx),
                "test_n": len(test_idx),
                "test_MAE_J": round(mae, 4),
                "test_RMSE_J": round(rmse, 4),
                "test_R2": round(r2, 4),
            })

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with (RESULTS_DIR / "cross_validation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fold_rows[0].keys())
        writer.writeheader()
        writer.writerows(fold_rows)

    summary: dict[str, dict[str, tuple[float, float, float]]] = {}
    for model_name, predicted in predictions.items():
        fold_metric_rows = [row for row in fold_rows if row["model"] == model_name]
        all_fold_values = {
            column: np.array([float(row[column]) for row in fold_metric_rows])
            for column in ("test_MAE_J", "test_RMSE_J", "test_R2")
        }
        summary[model_name] = {
            "all": metrics(y, predicted),
            "nested_loops": metrics(
                y[df["category"].eq("nested_loops").to_numpy()],
                predicted[df["category"].eq("nested_loops").to_numpy()],
            ),
        }
        summary[model_name]["mean_fold"] = tuple(
            float(values.mean()) for values in all_fold_values.values()
        )

    loop_series = pd.Series(loop_ops, index=df.index)
    report = [
        "# LoopOps predictor cross-validation",
        "",
        "This comparison aggregates the frozen five-run `raw_results.csv` (150 rows, 30 benchmarks) and reuses the category-stratified 5-fold split (24 train / 6 test per fold). No benchmark executions were repeated. The baseline uses normalized CC, ND, and FD. Added variants use raw AST-derived LoopOps or log10(1 + LoopOps) as a fourth predictor. Standardization is fit on each training fold only.",
        "",
        f"LoopOps range: {loop_series.min():.1f}–{loop_series.max():.1f}; median: {loop_series.median():.1f}.",
        f"The maximum is `{df.loc[loop_series.idxmax(), 'benchmark_id']}` in `{df.loc[loop_series.idxmax(), 'category']}`, showing how the assumed $10^{{depth}}$ weighting dominates deeply nested inputs.",
        "",
        "| Model | OOF MAE (J) | OOF RMSE (J) | OOF R² | Mean fold R² | Nested-loop OOF R² |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for model_name, label in (
        ("baseline", "CC + ND + FD"),
        ("with_raw_loopops", "CC + ND + FD + raw LoopOps"),
        ("with_log_loopops", "CC + ND + FD + log10(1 + LoopOps)"),
    ):
        mae, rmse, r2 = summary[model_name]["all"]
        mean_mae, mean_rmse, mean_r2 = summary[model_name]["mean_fold"]
        nested_mae, nested_rmse, nested_r2 = summary[model_name]["nested_loops"]
        report.append(f"| {label} | {mae:.4f} | {rmse:.4f} | {r2:.4f} | {mean_r2:.4f} | {nested_r2:.4f} |")
    report.extend([
        "",
        "OOF metrics pool each benchmark's held-out prediction; mean fold R² is the arithmetic mean of the five fold-specific R² scores, matching the prior report's summary convention. Nested-loop R² is descriptive only (n=5).",
        "",
        "LoopOps is a static assumed-iteration feature, not measured operation count. The visitor does not model recursive call depth; recursion-only work receives no recursion weighting.",
        "",
    ])
    (RESULTS_DIR / "report.md").write_text("\n".join(report), encoding="utf-8")

    print("LoopOps range:", f"{loop_series.min():.1f}–{loop_series.max():.1f}")
    for model_name, label in (
        ("baseline", "CC + ND + FD"),
        ("with_raw_loopops", "CC + ND + FD + raw LoopOps"),
        ("with_log_loopops", "CC + ND + FD + log10(1 + LoopOps)"),
    ):
        print(label, "OOF MAE/RMSE/R2:", *(round(value, 4) for value in summary[model_name]["all"]))
        print(label, "mean fold R2:", round(summary[model_name]["mean_fold"][2], 4),
              "nested loops OOF R2:", round(summary[model_name]["nested_loops"][2], 4))


if __name__ == "__main__":
    main()
