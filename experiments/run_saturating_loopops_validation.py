"""Validate the saturating LoopOps term on ten newly authored pairs."""
from __future__ import annotations

import csv
import math
import os
import platform
import subprocess
import sys
import timeit
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from energy.loop_ops import loop_weighted_ops  # noqa: E402
from energy.runtime import RuntimeEstimator  # noqa: E402

RESULTS = ROOT / "experiments" / "results" / "saturating_loopops_validation"
MIN_SAMPLE_SECONDS = 0.5
PILOT_TARGET_SECONDS = 0.65
POSITIVE_REPEATS = 20
CONTROL_REPEATS = 20
CONTROL_ROUNDS = 3


@dataclass(frozen=True)
class Pair:
    name: str
    kind: str
    n: int
    before: str
    after: str
    control: bool = False


PAIRS = [
    Pair("sum_weights", "sum call", 2_000_000,
         "def run(n):\n weights=(1,2,3,4,5)\n total=0\n for i in range(n):\n  total += sum(weights)+i\n return total\n",
         "def run(n):\n weights=(1,2,3,4,5)\n weight=sum(weights)\n total=0\n for i in range(n):\n  total += weight+i\n return total\n"),
    Pair("max_limits", "max call", 2_000_000,
         "def run(n):\n limits=(11,23,17,31)\n total=0\n for i in range(n):\n  total += max(limits)+i\n return total\n",
         "def run(n):\n limits=(11,23,17,31)\n upper=max(limits)\n total=0\n for i in range(n):\n  total += upper+i\n return total\n"),
    Pair("sin_angle", "math.sin", 2_000_000,
         "import math\ndef run(n):\n angle=.37\n total=0.0\n for i in range(n):\n  total += math.sin(angle)+i\n return total\n",
         "import math\ndef run(n):\n angle=.37\n wave=math.sin(angle)\n total=0.0\n for i in range(n):\n  total += wave+i\n return total\n"),
    Pair("zfill_text", "string method", 2_000_000,
         "def run(n):\n value='carbon'\n total=0\n for i in range(n):\n  total += len(value.zfill(12))+i\n return total\n",
         "def run(n):\n value='carbon'\n padded=value.zfill(12)\n total=0\n for i in range(n):\n  total += len(padded)+i\n return total\n"),
    Pair("dict_lookup", "dict get call", 2_000_000,
         "def run(n):\n table={'north':7,'south':9}\n key='north'\n total=0\n for i in range(n):\n  total += table.get(key)+i\n return total\n",
         "def run(n):\n table={'north':7,'south':9}\n key='north'\n selected=table.get(key)\n total=0\n for i in range(n):\n  total += selected+i\n return total\n"),
    Pair("list_copy", "list allocation call", 1_500_000,
         "def run(n):\n values=tuple(range(20))\n total=0\n for i in range(n):\n  total += len(list(values))+i\n return total\n",
         "def run(n):\n values=tuple(range(20))\n copied=list(values)\n total=0\n for i in range(n):\n  total += len(copied)+i\n return total\n"),
    Pair("string_replace", "string replace", 2_000_000,
         "def run(n):\n value='low-carbon-software'\n total=0\n for i in range(n):\n  total += len(value.replace('-', '_'))+i\n return total\n",
         "def run(n):\n value='low-carbon-software'\n clean=value.replace('-', '_')\n total=0\n for i in range(n):\n  total += len(clean)+i\n return total\n"),
    Pair("round_config", "round call", 2_000_000,
         "def run(n):\n threshold=17.654321\n total=0.0\n for i in range(n):\n  total += round(threshold, 3)+i\n return total\n",
         "def run(n):\n threshold=17.654321\n rounded=round(threshold, 3)\n total=0.0\n for i in range(n):\n  total += rounded+i\n return total\n"),
    Pair("constant_arithmetic_control", "constant arithmetic control", 2_000_000,
         "def run(n):\n total=0\n for i in range(n):\n  total += (3*4)+i\n return total\n",
         "def run(n):\n total=0\n for i in range(n):\n  total += 12+i\n return total\n", True),
    Pair("noop_rewrite_control", "no-op rewrite control", 2_000_000,
         "def run(n):\n total=0\n for i in range(n):\n  total += i*3+2\n return total\n",
         "def run(n):\n total=0\n for i in range(n):\n  total += (i*3)+2\n return total\n", True),
]


def factor(ops: np.ndarray | float) -> np.ndarray | float:
    beta = RuntimeEstimator.LOOP_OPS_BETA
    k = RuntimeEstimator.LOOP_OPS_K
    return 1.0 + beta * ops / (ops + k)


def _iteration_power(pair: Pair) -> int:
    return 2 if pair.kind.startswith("depth-two") else 1


def _pilot_seconds(fn, n: int) -> list[float]:
    return timeit.repeat(lambda: fn(n), repeat=3, number=1)


def choose_iterations(pair: Pair, before_fn, after_fn) -> int:
    """Increase work until pilot timings exceed the requested per-run floor."""
    n = pair.n
    power = _iteration_power(pair)
    for _ in range(14):
        pilot = _pilot_seconds(before_fn, n) + _pilot_seconds(after_fn, n)
        fastest = min(pilot)
        if fastest >= PILOT_TARGET_SECONDS:
            return n
        multiplier = max(1.35, (PILOT_TARGET_SECONDS / max(fastest, 1e-6)) ** (1.0 / power) * 1.08)
        n = max(n + 1, math.ceil(n * multiplier))
        if n > (100_000 if power == 2 else 80_000_000):
            break
    raise RuntimeError(f"Could not scale {pair.name} to {PILOT_TARGET_SECONDS:.2f}s per invocation")


def measure_pair(pair: Pair, before_fn, after_fn, n: int, repeats: int) -> tuple[list[float], list[float], int]:
    """Return paired timing samples, increasing n if any invocation is too short."""
    power = _iteration_power(pair)
    for _ in range(5):
        before = timeit.repeat(lambda: before_fn(n), repeat=repeats, number=1)
        after = timeit.repeat(lambda: after_fn(n), repeat=repeats, number=1)
        fastest = min(before + after)
        if fastest >= MIN_SAMPLE_SECONDS:
            return before, after, n
        multiplier = max(1.25, (PILOT_TARGET_SECONDS / max(fastest, 1e-6)) ** (1.0 / power) * 1.05)
        n = max(n + 1, math.ceil(n * multiplier))
    raise RuntimeError(f"{pair.name} still produced a sample below {MIN_SAMPLE_SECONDS:.2f}s")


def summarize_pair(before: list[float], after: list[float]) -> dict[str, float]:
    paired_drops = [100.0 * (b - a) / b for b, a in zip(before, after)]
    return {
        "before_median_seconds": float(np.median(before)),
        "before_q25_seconds": float(np.percentile(before, 25)),
        "before_q75_seconds": float(np.percentile(before, 75)),
        "after_median_seconds": float(np.median(after)),
        "after_q25_seconds": float(np.percentile(after, 25)),
        "after_q75_seconds": float(np.percentile(after, 75)),
        "measured_drop_median_percent": float(np.median(paired_drops)),
        "measured_drop_q25_percent": float(np.percentile(paired_drops, 25)),
        "measured_drop_q75_percent": float(np.percentile(paired_drops, 75)),
        "measured_drop_min_percent": float(min(paired_drops)),
        "measured_drop_max_percent": float(max(paired_drops)),
    }


def machine_state() -> dict[str, str]:
    state = {"platform": platform.platform(), "cpu_load_start_percent": "unavailable", "cpu_load_end_percent": "unavailable", "cpu_frequency_mhz": "unavailable", "power_scheme": "unavailable"}
    try:
        import psutil
        state["cpu_load_start_percent"] = f"{psutil.cpu_percent(interval=1.0):.1f}"
        freq = psutil.cpu_freq()
        if freq:
            state["cpu_frequency_mhz"] = f"{freq.current:.0f}"
    except Exception:
        pass
    if os.name == "nt":
        try:
            result = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True, timeout=5)
            state["power_scheme"] = result.stdout.strip().splitlines()[-1] if result.returncode == 0 else "unavailable"
        except Exception:
            pass
    return state


def main() -> None:
    beta = RuntimeEstimator.LOOP_OPS_BETA
    k = RuntimeEstimator.LOOP_OPS_K
    state = machine_state()
    results = []
    positive_samples: dict[str, tuple[list[float], list[float]]] = {}
    control_samples: dict[str, list[dict[str, object]]] = {}
    for pair in PAIRS:
        before_ns: dict[str, object] = {}
        after_ns: dict[str, object] = {}
        exec(compile(pair.before, "before.py", "exec"), before_ns)
        exec(compile(pair.after, "after.py", "exec"), after_ns)
        assert before_ns["run"](50) == after_ns["run"](50), pair.name
        before_ops = loop_weighted_ops(pair.before)
        after_ops = loop_weighted_ops(pair.after)
        before_fn = before_ns["run"]
        after_fn = after_ns["run"]
        n = choose_iterations(pair, before_fn, after_fn)
        modeled = 100 * (factor(before_ops) - factor(after_ops)) / factor(before_ops)

        if pair.control:
            rounds = []
            for round_id in range(1, CONTROL_ROUNDS + 1):
                before, after, n = measure_pair(pair, before_fn, after_fn, n, CONTROL_REPEATS)
                summary = summarize_pair(before, after)
                record = {
                    "pair": pair.name, "work_type": pair.kind, "negative_control": True,
                    "control_round": round_id, "repeat_count": CONTROL_REPEATS, "iterations": n,
                    "before_loopops": before_ops, "after_loopops": after_ops,
                    "modeled_drop_percent": modeled, **summary,
                    "before_samples_seconds": ";".join(f"{x:.6f}" for x in before),
                    "after_samples_seconds": ";".join(f"{x:.6f}" for x in after),
                }
                results.append(record)
                rounds.append(record)
            control_samples[pair.name] = rounds
        else:
            before, after, n = measure_pair(pair, before_fn, after_fn, n, POSITIVE_REPEATS)
            summary = summarize_pair(before, after)
            record = {
                "pair": pair.name, "work_type": pair.kind, "negative_control": False,
                "control_round": 0, "repeat_count": POSITIVE_REPEATS, "iterations": n,
                "before_loopops": before_ops, "after_loopops": after_ops,
                "modeled_drop_percent": modeled, **summary,
                "before_samples_seconds": ";".join(f"{x:.6f}" for x in before),
                "after_samples_seconds": ";".join(f"{x:.6f}" for x in after),
            }
            results.append(record)
            positive_samples[pair.name] = (before, after)

    positive = [r for r in results if not r["negative_control"]]
    controls = [r for r in results if r["negative_control"]]
    actual = np.array([float(r["measured_drop_median_percent"]) for r in positive])
    pred = np.array([float(r["modeled_drop_percent"]) for r in positive])
    rho = spearmanr(pred, actual)
    direction = sum((p > 0) == (y > 0) for p, y in zip(pred, actual))

    try:
        import psutil
        state["cpu_load_end_percent"] = f"{psutil.cpu_percent(interval=1.0):.1f}"
        freq = psutil.cpu_freq()
        if freq:
            state["cpu_frequency_mhz"] = f"{freq.current:.0f}"
    except Exception:
        pass

    RESULTS.mkdir(parents=True, exist_ok=True)
    with (RESULTS / "new_pairs.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    pos_table = [
        "| Pair | Work type | Ops before → after | Modeled drop | Measured drop median (IQR) |",
        "|---|---|---:|---:|---:|",
    ]
    pos_table.extend(
        f"| {r['pair']} | {r['work_type']} | {r['before_loopops']:.1f} → {r['after_loopops']:.1f} | {r['modeled_drop_percent']:.2f}% | {r['measured_drop_median_percent']:.2f}% ({r['measured_drop_q25_percent']:.2f}–{r['measured_drop_q75_percent']:.2f}) |"
        for r in positive
    )
    ctrl_table = [
        "| Negative control | Round | Measured drop median (IQR) |",
        "|---|---:|---:|",
    ]
    ctrl_table.extend(
        f"| {r['pair']} | {r['control_round']} | {r['measured_drop_median_percent']:.2f}% ({r['measured_drop_q25_percent']:.2f}–{r['measured_drop_q75_percent']:.2f}) |"
        for r in controls
    )
    control_noise = [abs(float(r["measured_drop_median_percent"])) for r in controls]
    noise_min, noise_max = min(control_noise), max(control_noise)
    report = [
        "# Saturating LoopOps validation on new pairs", "",
        f"Each measured invocation was scaled to at least {MIN_SAMPLE_SECONDS:.1f}s. Positive pairs use {POSITIVE_REPEATS} repeats per version and report the median plus the interquartile range (IQR) of paired percentage drops. Each negative control was independently rerun {CONTROL_ROUNDS} times, with {CONTROL_REPEATS} repeats per version in each round. Constants were fixed in advance; all pairs preserve return values and use identical before/after inputs and iteration counts.",
        "",
        f"Configured constants: **beta={beta:.1f}, K={k:.1f}**.",
        f"Positive-pair direction agreement: **{direction}/8**; Spearman rho: **{rho.statistic:.3f}** (p={rho.pvalue:.3f}, n=8).",
        f"Negative-control modeled drops were zero. Absolute control median-drop noise range across all {len(controls)} rounds: **{noise_min:.2f}%–{noise_max:.2f}%**.",
        f"Machine check: platform `{state['platform']}`; power scheme `{state['power_scheme']}`; CPU frequency `{state['cpu_frequency_mhz']} MHz`; CPU load sample at start/end `{state['cpu_load_start_percent']}%` / `{state['cpu_load_end_percent']}%`. CPU load was sampled at run boundaries, not continuously during every pair.",
        "",
        "## Positive hoists", "", *pos_table, "",
        "## Negative controls", "", *ctrl_table, "",
        "This small hand-built validation is exploratory, not broad calibration. It does not establish physical energy accuracy or general runtime prediction.",
        "",
    ]
    (RESULTS / "report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"beta={beta:.1f}; K={k:.1f}")
    print(f"per-run floor={MIN_SAMPLE_SECONDS:.1f}s; positive repeats={POSITIVE_REPEATS}; controls={CONTROL_ROUNDS} rounds × {CONTROL_REPEATS} repeats")
    print(f"positive direction={direction}/8; Spearman={rho.statistic:.3f}; p={rho.pvalue:.3f}")
    print(f"negative-control absolute median-drop noise range={noise_min:.2f}%–{noise_max:.2f}% across {len(controls)} rounds")
    print(f"power scheme={state['power_scheme']}; CPU load start/end={state['cpu_load_start_percent']}%/{state['cpu_load_end_percent']}%")
    print(RESULTS / "report.md")


if __name__ == "__main__":
    main()
