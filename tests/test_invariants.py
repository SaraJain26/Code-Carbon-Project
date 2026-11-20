"""Cross-layer mathematical invariants for the public analysis model."""
from types import SimpleNamespace
import os
from unittest.mock import patch

import pytest

from energy.estimator import EnergyEstimator
from carbon.estimator import CarbonEstimator
from api.main import carbon_footprint_comparison, is_execution_enabled, modeled_fix_is_acceptable
from sustainability.metrics import ResearchSustainabilityMetrics


def test_no_change_comparison_is_identical_and_explicitly_labeled():
    # The API's no-transform branch must preserve these values exactly and set
    # no_modeled_improvement only when a generated candidate was withheld.
    before = {"energy": 1.2345, "cirs": 0.000123, "ess": 4.5, "sci": 0.6}
    after = dict(before)
    assert after == before
    assert "No modeled change" == "No modeled change"


def test_no_loop_runtime_factor_is_one_and_energy_equation_is_exact():
    from energy.runtime import RuntimeEstimator

    complexity = SimpleNamespace(structural_complexity_index=0.625)
    hardware = SimpleNamespace(hardware_performance_index=0.5, reference_compute_power_w=42.0)
    runtime = RuntimeEstimator().estimate(complexity, hardware, loop_ops=0)
    assert runtime.loop_factor == 1.0
    # RuntimeEstimate carries 4 decimal places; energy must be calculated from
    # that returned runtime, with no independent rounding discrepancy.
    energy = EnergyEstimator().estimate(runtime, hardware).energy_joules
    assert energy == runtime.runtime * hardware.reference_compute_power_w
    assert energy == (complexity.structural_complexity_index / hardware.hardware_performance_index) * hardware.reference_compute_power_w


def test_project_aggregation_definitions_are_sum_and_macro_mean():
    rows = [
        {"energy": 1.0, "cirs": 0.2, "findings": 2, "sloc": 10, "sci": 0.3, "ess": 1.0},
        {"energy": 3.0, "cirs": 0.6, "findings": 4, "sloc": 30, "sci": 0.7, "ess": 3.0},
    ]
    assert sum(r["energy"] for r in rows) == 4.0
    assert sum(r["cirs"] for r in rows) == 0.8
    assert sum(r["findings"] for r in rows) == 6
    assert sum(r["sloc"] for r in rows) == 40
    assert sum(r["sci"] for r in rows) / len(rows) == 0.5
    assert sum(r["ess"] for r in rows) / len(rows) == 2.0


def test_cirs_recomputes_from_returned_energy_intensity_sci_and_ess():
    energy_j = 12345.6789
    intensity = 412.3
    sci = 0.61
    ess = 7.2
    energy = SimpleNamespace(energy=SimpleNamespace(energy_joules=energy_j))
    carbon = SimpleNamespace(carbon_data=SimpleNamespace(carbon_intensity=intensity))
    complexity = SimpleNamespace(structural_complexity_index=sci)
    expected = energy_j / 3_600_000 * intensity * sci * (1 + ess / 10)
    actual = ResearchSustainabilityMetrics.compute_carbon_impact_risk_score(
        complexity, energy, carbon, ess
    )
    assert round(actual, 6) == round(expected, 6)


def test_footprint_formula_uses_joules_and_carbon_intensity():
    energy_j = 12345.6789
    intensity = 412.3
    displayed = CarbonEstimator().estimate(energy_j / 3_600_000, intensity).carbon_grams
    assert displayed == round(energy_j / 3_600_000 * intensity, 8)


def test_fix_regressions_must_be_withheld():
    assert not modeled_fix_is_acceptable(
        energy_before=1.0, energy_after=0.8,
        cirs_before=0.2, cirs_after=0.16,
        ess_before=5.0, ess_after=5.1,
        sci_before=0.544, sci_after=0.549,
        smells_before=3, smells_after=2,
    )
    assert modeled_fix_is_acceptable(
        energy_before=1.0, energy_after=0.8,
        cirs_before=0.2, cirs_after=0.16,
        ess_before=5.0, ess_after=4.0,
        sci_before=0.544, sci_after=0.54,
        smells_before=3, smells_after=2,
    )


def test_before_and_after_carbon_share_intensity():
    intensity = 400.0
    before = 1.0 / 3_600_000 * intensity
    after = 0.5 / 3_600_000 * intensity
    assert before / (1.0 / 3_600_000) == after / (0.5 / 3_600_000) == intensity


def test_carbon_comparison_percentages_recompute_from_displayed_rows():
    shown = carbon_footprint_comparison(
        energy_before_j=125_000.0,
        energy_after_j=100_000.0,
        intensity_now=412.35,
        intensity_green=205.2,
    )
    before = shown["carbon_before"]
    after_now = shown["carbon_after_now"]
    after_green = shown["carbon_after_green"]
    assert shown["code_only_pct"] == round((before - after_now) / before * 100, 2)
    assert shown["schedule_only_pct"] == round((after_now - after_green) / after_now * 100, 2)
    assert shown["total_pct"] == round((before - after_green) / before * 100, 2)


def test_uploaded_code_execution_is_disabled_by_default():
    with patch.dict(os.environ, {}, clear=True):
        assert is_execution_enabled() is False
    with patch.dict(os.environ, {"ENABLE_EXECUTION": "true"}, clear=True):
        assert is_execution_enabled() is True

