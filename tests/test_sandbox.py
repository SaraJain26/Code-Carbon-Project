"""
Unit tests for SandboxedRuntimeExecutor in src/energy/sandbox.py.
"""

from energy.sandbox import SandboxedRuntimeExecutor


def test_sandbox_successful_execution():
    code = """
def run():
    acc = 0
    for i in range(100):
        acc += i
    return acc
run()
"""
    executor = SandboxedRuntimeExecutor(timeout_sec=2.0)
    res = executor.execute_sandboxed(code)

    assert res.status == "success"
    assert res.wall_time_ms >= 0.0
    assert res.cpu_time_ms >= 0.0
    assert res.memory_kb >= 0.0


def test_sandbox_timeout_handling():
    hanging_code = """
import time
while True:
    time.sleep(0.01)
"""
    executor = SandboxedRuntimeExecutor(timeout_sec=0.5)
    res = executor.execute_sandboxed(hanging_code)

    assert res.status == "timeout"
    assert "timed out" in (res.error_message or "")


def test_sandbox_measure_comparison():
    orig_code = """
res = []
for i in range(50):
    val = 3.14159 * 42.0
    res.append(i * val)
"""
    opt_code = """
res = []
val = 3.14159 * 42.0
for i in range(50):
    res.append(i * val)
"""
    executor = SandboxedRuntimeExecutor(timeout_sec=2.0)
    comp = executor.measure_comparison(orig_code, opt_code)

    assert comp["is_sandboxed"] is True
    assert "original" in comp
    assert "optimized" in comp
    assert "measured_savings" in comp
    assert comp["original"]["status"] == "success"
    assert comp["optimized"]["status"] == "success"


def test_sandbox_measurement_reliability_small_and_large():
    executor = SandboxedRuntimeExecutor(timeout_sec=2.0)

    # 1. Fast / Small workload (runtime < 50ms) -> low_confidence_small_workload
    small_orig = "x = 1 + 1"
    small_opt = "x = 2"
    res_small = executor.measure_comparison(small_orig, small_opt)

    assert res_small["measurement_reliability"] == "low_confidence_small_workload"
    assert res_small["reliability_threshold_ms"] == 50.0
    assert "below the 50ms empirical reliability threshold" in res_small["reliability_note"] or "below the 50" in res_small["reliability_note"]

    # 2. Longer-running / Large workload (runtime >= 50ms) -> reliable
    large_orig = """
import time
time.sleep(0.08)
"""
    large_opt = """
import time
time.sleep(0.08)
"""
    res_large = executor.measure_comparison(large_orig, large_opt)

    assert res_large["measurement_reliability"] == "reliable"
    assert res_large["reliability_threshold_ms"] == 50.0
    assert "exceeds the 50ms empirical reliability threshold" in res_large["reliability_note"] or "exceeds the 50" in res_large["reliability_note"]

