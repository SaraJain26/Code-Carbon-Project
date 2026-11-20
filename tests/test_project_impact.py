from unittest.mock import patch

from api.main import build_project_scheduling, modeled_fix_is_acceptable, modeled_fix_status, run_project_analysis


def _analysis(before_energy, after_energy, before_cirs, after_cirs, before_ess, after_ess, status, reason):
    return {
        "research_metrics": {
            "energy_smell_score": before_ess,
            "carbon_impact_risk_score": before_cirs,
        },
        "post_refactor_estimation": {
            "energy_before_joules": before_energy,
            "energy_after_joules": after_energy,
            "sci_before": 0.5,
            "cirs_after": after_cirs,
            "ess_after": after_ess,
            "fix_status": status,
            "fix_reason": reason,
            "carbon_metadata": {
                "carbon_intensity": 400.0,
                "zone": "IN",
                "source": "test",
                "source_type": "mock",
            },
        },
        "pipeline_raw": {
            "complexity_metrics": {"lines_of_code": 3},
            "energy_smell_report": {"findings": []},
        },
        "auto_applied_fixes": [{"rule_id": "TEST"}] if status == "applied" else [],
    }


def _project(files, analyses):
    def fake_analyze(filename, source, **_kwargs):
        return analyses[filename]

    with patch("api.main.run_single_file_analysis", side_effect=fake_analyze), patch(
        "api.main.build_project_scheduling", return_value={"status": "unavailable"}
    ):
        return run_project_analysis(
            [(filename, source.encode()) for filename, source in files],
            "sample.zip",
            "IN",
            False,
            0.0,
        )


def test_two_file_project_aggregates_accepted_after_values():
    payload = _project(
        [("fixed.py", "pass"), ("unchanged.py", "pass")],
        {
            "fixed.py": _analysis(100, 70, 10, 7, 4, 3, "applied", "Improved modeled metrics."),
            "unchanged.py": _analysis(50, 50, 5, 5, 2, 2, "not_auto_fixable", "No safe automatic fix."),
        },
    )
    assert payload["project_before"] == {"energy": 150.0, "cirs": 15.0, "ess": 6.0}
    assert payload["project_after"] == {"energy": 120.0, "cirs": 12.0, "ess": 5.0}
    assert payload["project_delta"] == {"energy": -30.0, "cirs": -3.0, "ess": -1.0}
    fixed, unchanged = payload["files"]
    assert fixed["fix_status"] == "applied"
    assert unchanged["fix_status"] == "not_auto_fixable"
    assert unchanged["fix_reason"] == "No safe automatic fix."
    assert payload["auto_fixable_count"] == 1
    assert payload["auto_applied_count"] == 1


def test_project_with_no_accepted_fix_preserves_totals_and_reasons():
    payload = _project(
        [("one.py", "pass"), ("two.py", "pass")],
        {
            "one.py": _analysis(20, 20, 2, 2, 1, 1, "not_auto_fixable", "No safe automatic fix."),
            "two.py": _analysis(30, 30, 3, 3, 2, 2, "rejected_no_improvement", "Candidate did not improve modeled energy or CIRS."),
        },
    )
    assert payload["project_after"] == payload["project_before"]
    assert payload["project_delta"] == {"energy": 0.0, "cirs": 0.0, "ess": 0.0}
    assert payload["auto_applied_count"] == 0
    assert [item["fix_reason"] for item in payload["files"]] == [
        "No safe automatic fix.",
        "Candidate did not improve modeled energy or CIRS.",
    ]


def test_candidate_regressed_metric_is_rejected_with_reason():
    status, reason = modeled_fix_status(
        candidate_generated=True,
        accepted=False,
        energy_before=100,
        energy_after=90,
        cirs_before=10,
        cirs_after=9,
        ess_before=4,
        ess_after=4.5,
        sci_before=0.5,
        sci_after=0.4,
        smells_before=2,
        smells_after=1,
    )
    assert status == "rejected_regression"
    assert "ESS" in reason
    assert not modeled_fix_is_acceptable(
        energy_before=100,
        energy_after=90,
        cirs_before=10,
        cirs_after=9,
        ess_before=4,
        ess_after=4.5,
        sci_before=0.5,
        sci_after=0.4,
        smells_before=2,
        smells_after=1,
    )


def test_project_scheduling_uses_cleaner_forecast_intensity():
    forecast = {
        "zone": "IN",
        "current_carbon_intensity": 430.0,
        "lowest_forecast_intensity": 301.0,
        "percentage_reduction": 30.0,
        "recommended_execution_time": "2026-11-20T10:00:00+00:00",
        "hourly_forecasts": [],
        "source": "Electricity Maps",
        "source_type": "live",
    }
    with patch("api.main.build_forecast_response", return_value=forecast):
        scheduling = build_project_scheduling("IN", 80.0, 424.0, "Electricity Maps", "live")
    assert scheduling["has_cleaner_window"] is True
    assert scheduling["intensity_now"] == 424.0
    assert scheduling["intensity_window"] == 301.0
    assert scheduling["scheduling_reduction_percent"] == 29.01
    assert scheduling["source_type"] == "live"


def test_project_scheduling_keeps_current_intensity_when_no_cleaner_window():
    forecast = {
        "zone": "IN",
        "current_carbon_intensity": 455.0,
        "lowest_forecast_intensity": 455.0,
        "percentage_reduction": 0.0,
        "recommended_execution_time": "2026-11-20T10:00:00+00:00",
        "hourly_forecasts": [],
        "source": "mock forecast",
        "source_type": "mock",
    }
    with patch("api.main.build_forecast_response", return_value=forecast):
        scheduling = build_project_scheduling("IN", 80.0, 424.0, "Electricity Maps", "live")
    assert scheduling["has_cleaner_window"] is False
    assert scheduling["intensity_window"] == 424.0
    assert scheduling["scheduling_reduction_percent"] == 0.0
    assert scheduling["window_start"] is None
