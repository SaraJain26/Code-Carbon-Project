"""
FastAPI Backend Layer for Code-Carbon.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import math
import sys
import time
import zipfile
import io
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_SRC_DIR = Path(__file__).resolve().parent.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

logger = logging.getLogger("codecarbon.api")

import ast
from dataclasses import replace
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query, APIRouter
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from carbon import get_carbon_provider, MockCarbonIntensityProvider
from pipeline import PredictivePipeline
from recommendation.engine import RecommendationEngine
from recommendation.transformer import ASTCodeTransformer
from recommendation.location_suggestions import build_location_suggestions
from energy.sandbox import SandboxedRuntimeExecutor
from energy.loop_ops import loop_weighted_ops
from sustainability.metrics import ResearchSustainabilityMetrics
from energy.models import EnergyResult, EnergyEstimate, RuntimeEstimate
from knowledge.loader import RuleLoader
from .utils import serialize_value
from .models import HealthResponse, AnalyzeResponse, ForecastResponse, ProjectAnalyzeResponse, ProjectFileResult

try:
    _ekb_rules = RuleLoader().load_default_rules()
    EKB_RULE_NAMES: dict[str, str] = {rule.id: rule.name for rule in _ekb_rules}
except Exception:
    EKB_RULE_NAMES = {}

import sys
import asyncio
from contextlib import asynccontextmanager

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    def custom_exception_handler(loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
        exc = context.get("exception")
        if isinstance(exc, OSError) and getattr(exc, "winerror", None) in (64, 10054, 10053, 10058):
            return
        loop.default_exception_handler(context)
    loop.set_exception_handler(custom_exception_handler)
    yield

app = FastAPI(
    title="Code-Carbon API",
    description="Sustainability-First Framework for Predictive Carbon-Aware Software Engineering",
    version="0.1.0",
    lifespan=lifespan
)

router = APIRouter()


def modeled_fix_is_acceptable(
    *, energy_before: float, energy_after: float, cirs_before: float, cirs_after: float,
    ess_before: float, ess_after: float, sci_before: float, sci_after: float,
    smells_before: int, smells_after: int,
    cc_before: float = 0.0, cc_after: float = 0.0,
    nd_before: float = 0.0, nd_after: float = 0.0,
    fd_before: float = 0.0, fd_after: float = 0.0,
    findings_before: int = 0, findings_after: int = 0,
    smell_burden_before: float = 0.0, smell_burden_after: float = 0.0,
    loop_ops_before: float = 0.0, loop_ops_after: float = 0.0,
) -> bool:
    """Accept only a modeled improvement without regressions in protected metrics."""
    return (
        energy_after <= energy_before + 1e-9
        and cirs_after <= cirs_before + 1e-12
        and ess_after <= ess_before + 1e-9
        and sci_after <= sci_before + 1e-9
        and smells_after <= smells_before
        and cc_after <= cc_before + 1e-9
        and nd_after <= nd_before
        and fd_after <= fd_before + 1e-9
        and findings_after <= findings_before
        and smell_burden_after <= smell_burden_before + 1e-9
        and loop_ops_after <= loop_ops_before + 1e-9
        and (
            energy_after < energy_before - 1e-9
            or cirs_after < cirs_before - 1e-12
        )
    )


def modeled_fix_status(
    *, candidate_generated: bool, accepted: bool = False,
    energy_before: float = 0.0, energy_after: float = 0.0,
    cirs_before: float = 0.0, cirs_after: float = 0.0,
    ess_before: float = 0.0, ess_after: float = 0.0,
    sci_before: float = 0.0, sci_after: float = 0.0,
    smells_before: int = 0, smells_after: int = 0,
    cc_before: float = 0.0, cc_after: float = 0.0,
    nd_before: float = 0.0, nd_after: float = 0.0,
    fd_before: float = 0.0, fd_after: float = 0.0,
    findings_before: int = 0, findings_after: int = 0,
    smell_burden_before: float = 0.0, smell_burden_after: float = 0.0,
    loop_ops_before: float = 0.0, loop_ops_after: float = 0.0,
) -> tuple[str, str]:
    """Explain whether a generated AST fix was retained by the modeled quality gate."""
    if not candidate_generated:
        return "not_auto_fixable", "No safe automatic AST transformation was available for this file."
    if accepted:
        return "applied", "The automatic change improved modeled energy or CIRS without regressing a protected metric."

    regressed = []
    if energy_after > energy_before + 1e-9:
        regressed.append("energy")
    if cirs_after > cirs_before + 1e-12:
        regressed.append("CIRS")
    if ess_after > ess_before + 1e-9:
        regressed.append("ESS")
    if sci_after > sci_before + 1e-9:
        regressed.append("SCI")
    if smells_after > smells_before:
        regressed.append("actionable smell count")
    if cc_after > cc_before + 1e-9:
        regressed.append("cyclomatic complexity")
    if nd_after > nd_before:
        regressed.append("nesting depth")
    if fd_after > fd_before + 1e-9:
        regressed.append("function density")
    if findings_after > findings_before:
        regressed.append("finding locations")
    if smell_burden_after > smell_burden_before + 1e-9:
        regressed.append("smell burden")
    if loop_ops_after > loop_ops_before + 1e-9:
        regressed.append("loop operation estimate")
    if regressed:
        return "rejected_regression", f"Candidate was rejected because it regressed {', '.join(regressed)}."
    return "rejected_no_improvement", "Candidate did not improve modeled energy or CIRS."


def carbon_footprint_comparison(
    energy_before_j: float,
    energy_after_j: float,
    intensity_now: float,
    intensity_green: float,
) -> dict[str, float]:
    """Return the three unweighted modeled footprints and their matching reductions."""
    before = round(energy_before_j / 3_600_000.0 * intensity_now, 9)
    after_now = round(energy_after_j / 3_600_000.0 * intensity_now, 9)
    after_green = round(energy_after_j / 3_600_000.0 * intensity_green, 9)
    code_pct = (before - after_now) / before * 100.0 if before else 0.0
    schedule_pct = (after_now - after_green) / after_now * 100.0 if after_now else 0.0
    total_pct = (before - after_green) / before * 100.0 if before else 0.0
    return {
        "carbon_before": before,
        "carbon_after_now": after_now,
        "carbon_after_green": after_green,
        "code_only_pct": round(code_pct, 2),
        "schedule_only_pct": round(schedule_pct, 2),
        "total_pct": round(total_pct, 2),
    }


def is_execution_enabled() -> bool:
    """Uploaded-code execution is opt-in and disabled unless explicitly enabled."""
    return os.environ.get("ENABLE_EXECUTION", "false").strip().lower() in {"1", "true", "yes", "on", "enabled"}

# Enable CORS for frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173", "http://127.0.0.1:4173", "*"],
    allow_credentials=False,
    allow_headers=["*"],
    allow_methods=["*"],
)


@router.api_route("/health", methods=["GET", "HEAD"], response_model=HealthResponse, tags=["General"])
def get_health() -> dict[str, str]:
    """
    Check the health of the Code-Carbon API server.
    """
    return {"status": "healthy"}


@router.get("/zones", tags=["Electricity Maps"])
def get_zones() -> dict[str, Any]:
    """
    Retrieve all supported Electricity Maps zones.
    """
    try:
        client = get_carbon_provider()
        zones = client.get_all_zones()
        return serialize_value(zones)
    except Exception as exc:
        logger.warning("Live carbon provider failed in /zones (%s). Falling back to mock provider.", exc)
        try:
            return serialize_value(MockCarbonIntensityProvider().get_all_zones())
        except Exception as inner_exc:
            raise HTTPException(status_code=500, detail=str(inner_exc))


@router.get("/search-zones", tags=["Electricity Maps"])
def search_zones(q: str = Query(..., min_length=1)) -> dict[str, Any]:
    """
    Search supported Electricity Maps zones by country or code.
    """
    try:
        client = get_carbon_provider()
        matches = client.search_zones(q)
        return serialize_value(matches)
    except Exception as exc:
        logger.warning("Live carbon provider failed in /search-zones (%s). Falling back to mock provider.", exc)
        try:
            return serialize_value(MockCarbonIntensityProvider().search_zones(q))
        except Exception as inner_exc:
            raise HTTPException(status_code=500, detail=str(inner_exc))


def run_single_file_analysis(
    filename: str,
    source_code: str,
    zone: str = "DK-DK1",
    use_global_average: bool = True,
    measure_runtime: bool = True,
) -> dict[str, Any]:
    """
    Core single file analysis logic: static analysis, carbon estimation, AST transformation, and sandboxed measurement.
    """
    stage_timings_sec: dict[str, float] = {}
    stage_start = time.perf_counter()
    try:
        parsed_tree = ast.parse(source_code, filename=filename)
        stage_timings_sec["preflight_parse"] = time.perf_counter() - stage_start
    except SyntaxError as se:
        raise HTTPException(status_code=400, detail=f"Python syntax error: {se}")

    workspace_temp_dir = Path("temp_analysis")
    workspace_temp_dir.mkdir(exist_ok=True)

    temp_path = workspace_temp_dir / f"temp_{datetime.now().timestamp()}_{filename}"

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(source_code)

        pipeline = PredictivePipeline()
        stage_start = time.perf_counter()
        result = pipeline.run(
            source_file=temp_path,
            zone=zone,
            use_global_average=use_global_average,
            parsed_tree=parsed_tree,
        )
        stage_timings_sec["analysis"] = time.perf_counter() - stage_start

        smell_report = result["energy_smell_report"]
        complexity_score = result["complexity_score"]
        energy_result = result["energy_result"]
        carbon_result = result["carbon_result"]

        ess = ResearchSustainabilityMetrics.compute_energy_smell_score(smell_report)
        cirs_research = ResearchSustainabilityMetrics.compute_carbon_impact_risk_score(
            complexity=complexity_score,
            energy_result=energy_result,
            carbon_result=carbon_result,
            ess=ess
        )

        engine = RecommendationEngine()
        recommendation_report = engine.generate(
            smell_report=smell_report,
            complexity=complexity_score,
            energy_result=energy_result,
            carbon_result=carbon_result
        )

        # Run AST Code Transformer for safe automated code fixes
        raw_findings = [serialize_value(f) for f in smell_report.findings]
        transformer = ASTCodeTransformer()
        stage_start = time.perf_counter()
        transform_res = transformer.transform(source_code, findings=raw_findings)
        auto_fix_candidate_count = len(transform_res.auto_applied_fixes)
        stage_timings_sec["transform"] = time.perf_counter() - stage_start

        # Automatically execute real measurement in isolated sandboxed subprocesses
        execution_enabled = is_execution_enabled()
        if measure_runtime and execution_enabled:
            sandbox_executor = SandboxedRuntimeExecutor(timeout_sec=2.0)
            measured_runtime = sandbox_executor.measure_comparison(
                original_code=source_code,
                optimized_code=transform_res.optimized_code
            )
        elif not execution_enabled:
            measured_runtime = {
                "is_sandboxed": False,
                "measurement_reliability": "disabled",
                "reliability_threshold_ms": SandboxedRuntimeExecutor.RELIABILITY_THRESHOLD_MS,
                "reliability_note": "Not executed (static analysis only). Set ENABLE_EXECUTION=true to opt in to sandboxed measurement.",
                "execution_status": "not_executed",
                "energy_method": "Not executed (static analysis only)",
                "original": {"status": "not_executed"},
                "optimized": {"status": "not_executed"},
                "measured_savings": {"time_reduction_percent": 0.0, "energy_reduction_percent": 0.0},
            }
        else:
            measured_runtime = {
                "is_sandboxed": False,
                "measurement_reliability": "unavailable",
                "reliability_threshold_ms": SandboxedRuntimeExecutor.RELIABILITY_THRESHOLD_MS,
                "execution_status": "not_executed",
                "reliability_note": (
                    "Runtime timing was skipped for project analysis because files were analyzed concurrently; "
                    "run this file individually for an uncontended timing comparison."
                ),
                "energy_method": "Not measured during concurrent project analysis",
                "measured_savings": {"time_reduction_percent": 0.0, "energy_reduction_percent": 0.0},
            }

        # Reuse the existing analysis when the transformer made no automatic
        # change. A changed source needs a fresh after-pass for its metrics.
        temp_opt_path = workspace_temp_dir / f"temp_opt_{datetime.now().timestamp()}_{filename}"

        try:
            stage_timings_sec["re_analysis"] = 0.0
            if transform_res.auto_applied_fixes:
                with open(temp_opt_path, "w", encoding="utf-8") as f:
                    f.write(transform_res.optimized_code)
                stage_start = time.perf_counter()
                result_after = pipeline.run(
                    source_file=temp_opt_path,
                    zone=zone,
                    use_global_average=use_global_average
                )
                stage_timings_sec["re_analysis"] = time.perf_counter() - stage_start
            else:
                result_after = result

            smell_report_after = result_after["energy_smell_report"]
            complexity_score_after = result_after["complexity_score"]
            complexity_metrics_after = result_after["complexity_metrics"]
            energy_result_after = result_after["energy_result"]

            ess_after = ResearchSustainabilityMetrics.compute_energy_smell_score(smell_report_after)

            intensity = carbon_result.carbon_data.carbon_intensity
            energy_joules_before = energy_result.energy.energy_joules
            energy_joules_after = energy_result_after.energy.energy_joules
            energy_kwh_before = energy_joules_before / 3_600_000.0
            energy_kwh_after = energy_joules_after / 3_600_000.0

            sci_before = complexity_score.structural_complexity_index
            sci_after = complexity_score_after.structural_complexity_index

            fd_before = getattr(result["complexity_metrics"], "function_density", 0.0)
            fd_after = getattr(complexity_metrics_after, "function_density", 0.0)
            loop_ops_before = loop_weighted_ops(source_code)
            loop_ops_after = loop_weighted_ops(transform_res.optimized_code)
            structural_trace = {
                "candidate_generated": bool(transform_res.auto_applied_fixes),
                "before": {
                    "cc": getattr(result["complexity_metrics"], "cyclomatic_complexity", 0.0),
                    "nd": getattr(result["complexity_metrics"], "max_nesting_depth", 0),
                    "fd": fd_before,
                    "loop_ops": loop_ops_before,
                },
                "after": {
                    "cc": getattr(complexity_metrics_after, "cyclomatic_complexity", 0.0),
                    "nd": getattr(complexity_metrics_after, "max_nesting_depth", 0),
                    "fd": fd_after,
                    "loop_ops": loop_ops_after,
                },
            }
            logger.info(
                "[Transform Metrics] CC %(cc_before)s -> %(cc_after)s | ND %(nd_before)s -> %(nd_after)s | "
                "FD %(fd_before)s -> %(fd_after)s | LoopOps %(ops_before)s -> %(ops_after)s",
                {
                    "cc_before": structural_trace["before"]["cc"],
                    "cc_after": structural_trace["after"]["cc"],
                    "nd_before": structural_trace["before"]["nd"],
                    "nd_after": structural_trace["after"]["nd"],
                    "fd_before": structural_trace["before"]["fd"],
                    "fd_after": structural_trace["after"]["fd"],
                    "ops_before": loop_ops_before,
                    "ops_after": loop_ops_after,
                },
            )

            if transform_res.auto_applied_fixes:
                temp_base_path = workspace_temp_dir / f"temp_base_{datetime.now().timestamp()}_{filename}"
                try:
                    stage_start = time.perf_counter()
                    baseline_tree = parsed_tree
                    baseline_code = ast.unparse(parsed_tree)
                    with open(temp_base_path, "w", encoding="utf-8") as bf:
                        bf.write(baseline_code)

                    result_baseline = pipeline.run(
                        source_file=temp_base_path,
                        zone=zone,
                        use_global_average=use_global_average,
                        parsed_tree=baseline_tree,
                    )
                    stage_timings_sec["baseline"] = time.perf_counter() - stage_start

                    sci_baseline = result_baseline["complexity_score"].structural_complexity_index
                    energy_baseline = result_baseline["energy_result"].energy.energy_joules
                    fd_baseline = getattr(result_baseline["complexity_metrics"], "function_density", 0.0)

                    sci_after = max(0.0, sci_before + (sci_after - sci_baseline))
                    energy_joules_after = max(0.0, energy_joules_before + (energy_joules_after - energy_baseline))
                    fd_after = max(0.0, fd_before + (fd_after - fd_baseline))
                    energy_kwh_after = energy_joules_after / 3_600_000.0
                except Exception as exc:
                    stage_timings_sec.setdefault("baseline", 0.0)
                    logger.warning("Reformatted baseline normalization failed: %s", exc)
                finally:
                    if temp_base_path.exists():
                        try:
                            temp_base_path.unlink()
                        except Exception:
                            pass

            else:
                stage_timings_sec["baseline"] = 0.0
                # No source change means every modeled before/after value must
                # remain exactly equal, even if separate analysis passes drift.
                ess_after = ess
                sci_after = sci_before
                energy_joules_after = energy_joules_before
                energy_kwh_after = energy_kwh_before
                fd_after = fd_before

            exposure_before = sci_before * (1.0 + (ess / 10.0))
            exposure_after = sci_after * (1.0 + (ess_after / 10.0))

            # Pick the green window based on forecast intensity, then apply that
            # intensity directly to the after-code energy and exposure estimate.
            window_start: str | None = None
            window_end: str | None = None
            best_intensity = intensity
            try:
                after_forecasts = pipeline._carbon_engine.forecast(
                    energy_result_after,
                    zone=zone,
                )
                best_window = pipeline._carbon_engine.best_execution_window(after_forecasts)
                best_intensity = best_window.carbon_data.carbon_intensity
                start_dt = best_window.carbon_data.timestamp
                window_start = start_dt.isoformat()
                window_end = (start_dt + timedelta(hours=1)).isoformat()
            except Exception as exc:
                logger.warning("Forecast unavailable during analysis; using current intensity for green-window estimate: %s", exc)

            def research_cirs(energy_kwh: float, carbon_intensity: float, exposure: float) -> float:
                return energy_kwh * carbon_intensity * exposure

            cirs_before = research_cirs(energy_kwh_before, intensity, exposure_before)
            cirs_after = research_cirs(energy_kwh_after, intensity, exposure_after)

            no_modeled_improvement = False
            withheld_rule_ids: set[str] = set()
            fix_status, fix_reason = modeled_fix_status(
                candidate_generated=bool(transform_res.auto_applied_fixes),
            )
            if transform_res.auto_applied_fixes:
                smells_before_gate = sum(getattr(f.confidence, "value", 0.0) >= 0.5 for f in smell_report.findings)
                smells_after_gate = sum(getattr(f.confidence, "value", 0.0) >= 0.5 for f in smell_report_after.findings)
                accept_modeled_fix = modeled_fix_is_acceptable(
                    energy_before=energy_joules_before,
                    energy_after=energy_joules_after,
                    cirs_before=cirs_before,
                    cirs_after=cirs_after,
                    ess_before=ess,
                    ess_after=ess_after,
                    sci_before=sci_before,
                    sci_after=sci_after,
                    smells_before=smells_before_gate,
                    smells_after=smells_after_gate,
                    cc_before=getattr(result["complexity_metrics"], "cyclomatic_complexity", 0.0),
                    cc_after=getattr(complexity_metrics_after, "cyclomatic_complexity", 0.0),
                    nd_before=getattr(result["complexity_metrics"], "max_nesting_depth", 0),
                    nd_after=getattr(complexity_metrics_after, "max_nesting_depth", 0),
                    fd_before=fd_before,
                    fd_after=fd_after,
                    findings_before=len(smell_report.findings),
                    findings_after=len(smell_report_after.findings),
                    smell_burden_before=sum(getattr(f.confidence, "value", 0.0) for f in smell_report.findings),
                    smell_burden_after=sum(getattr(f.confidence, "value", 0.0) for f in smell_report_after.findings),
                    loop_ops_before=loop_ops_before,
                    loop_ops_after=loop_ops_after,
                )
                fix_status, fix_reason = modeled_fix_status(
                    candidate_generated=True,
                    accepted=accept_modeled_fix,
                    energy_before=energy_joules_before,
                    energy_after=energy_joules_after,
                    cirs_before=cirs_before,
                    cirs_after=cirs_after,
                    ess_before=ess,
                    ess_after=ess_after,
                    sci_before=sci_before,
                    sci_after=sci_after,
                    smells_before=smells_before_gate,
                    smells_after=smells_after_gate,
                    cc_before=getattr(result["complexity_metrics"], "cyclomatic_complexity", 0.0),
                    cc_after=getattr(complexity_metrics_after, "cyclomatic_complexity", 0.0),
                    nd_before=getattr(result["complexity_metrics"], "max_nesting_depth", 0),
                    nd_after=getattr(complexity_metrics_after, "max_nesting_depth", 0),
                    fd_before=fd_before,
                    fd_after=fd_after,
                    findings_before=len(smell_report.findings),
                    findings_after=len(smell_report_after.findings),
                    smell_burden_before=sum(getattr(f.confidence, "value", 0.0) for f in smell_report.findings),
                    smell_burden_after=sum(getattr(f.confidence, "value", 0.0) for f in smell_report_after.findings),
                    loop_ops_before=loop_ops_before,
                    loop_ops_after=loop_ops_after,
                )
                if not accept_modeled_fix:
                    no_modeled_improvement = True
                    withheld_rule_ids = {fix.get("rule_id", "") for fix in transform_res.auto_applied_fixes}
                    transform_res.optimized_code = source_code
                    transform_res.auto_applied_fixes = []
                    transform_res.manual_fixes = [
                        fix for fix in transform_res.manual_fixes
                        if fix.get("rule_id") not in withheld_rule_ids
                    ]
                    result_after = result
                    smell_report_after = smell_report
                    complexity_score_after = complexity_score
                    complexity_metrics_after = result["complexity_metrics"]
                    energy_result_after = energy_result
                    ess_after = ess
                    sci_after = sci_before
                    energy_joules_after = energy_joules_before
                    energy_kwh_after = energy_kwh_before
                    fd_after = fd_before
                    exposure_after = exposure_before
                    cirs_after = cirs_before

                    if measure_runtime and execution_enabled:
                        measured_runtime = {
                            "is_sandboxed": True,
                            "measurement_reliability": "unavailable",
                            "reliability_threshold_ms": SandboxedRuntimeExecutor.RELIABILITY_THRESHOLD_MS,
                            "reliability_note": "Candidate transformation was withheld because it did not improve both modeled energy and CIRS without a regression.",
                            "energy_method": "No transformation retained",
                            "measured_savings": {"time_reduction_percent": 0.0, "energy_reduction_percent": 0.0},
                        }
                    recommendation_list = [
                        rec for rec in recommendation_report.recommendations
                        if rec.rule_id not in withheld_rule_ids
                    ]
                    summary = (
                        "No automatic refactor was retained because its modeled energy and CIRS did not improve without a regression."
                        if not recommendation_list else
                        f"Detected {len(recommendation_list)} remaining recommendation area(s); modeled-negative automatic changes were withheld."
                    )
                    recommendation_report = replace(
                        recommendation_report,
                        recommendations=recommendation_list,
                        summary=summary,
                    )
                    logger.info(
                        "[Transform Withheld] modeled before/after did not Pareto-improve energy and CIRS; rules=%s",
                        sorted(withheld_rule_ids),
                    )
            structural_trace["candidate_accepted"] = bool(structural_trace["candidate_generated"] and not no_modeled_improvement)

            cirs_after_green = research_cirs(energy_kwh_after, best_intensity, exposure_after)
            hazard_before = energy_kwh_before * intensity
            hazard_after = energy_kwh_after * intensity

            logger.info(
                f"[CIRS Breakdown] E_kWh: {energy_kwh_before:.8f} -> {energy_kwh_after:.8f} | "
                f"SCI: {sci_before:.4f} -> {sci_after:.4f} | "
                f"Hazard: {hazard_before:.6f} -> {hazard_after:.6f} | "
                f"Exposure: {exposure_before:.4f} -> {exposure_after:.4f} | "
                f"CIRS: {cirs_before:.6f} -> {cirs_after:.6f}"
            )

            predicted_reduction_percent = round(((cirs_before - cirs_after) / cirs_before) * 100.0, 1) if cirs_before > 0 else 0.0
            measured_reduction_percent = measured_runtime.get("measured_savings", {}).get("time_reduction_percent", 0.0)
            footprint_comparison = carbon_footprint_comparison(
                energy_joules_before, energy_joules_after, intensity, best_intensity
            )
            code_only_pct = footprint_comparison["code_only_pct"]
            schedule_only_pct = footprint_comparison["schedule_only_pct"]
            total_pct = footprint_comparison["total_pct"]

            metric_changes = {
                "complexity_changed": not math.isclose(sci_before, sci_after, abs_tol=1e-9),
                "energy_changed": not math.isclose(energy_joules_before, energy_joules_after, abs_tol=1e-9),
                "energy_smell_changed": not math.isclose(ess, ess_after, abs_tol=1e-9),
                "carbon_risk_changed": not math.isclose(cirs_before, cirs_after, abs_tol=1e-12),
            }

            # Build rule-aligned findings comparison matching recommendation report
            findings_after_confidence: dict[str, float] = {}
            for finding in smell_report_after.findings:
                rule_id = finding.rule_id
                confidence = float(getattr(finding.confidence, "value", 0.0))
                findings_after_confidence[rule_id] = max(
                    confidence,
                    findings_after_confidence.get(rule_id, 0.0),
                )

            findings_comparison = []
            for rec in recommendation_report.recommendations:
                f_line = getattr(rec, "line_number", None)
                if f_line is None and hasattr(rec, "findings") and rec.findings:
                    f_line = getattr(rec.findings[0], "line_number", None)

                confidence_after = findings_after_confidence.get(rec.rule_id, 0.0)
                is_resolved = rec.rule_id not in findings_after_confidence

                conf_before = getattr(rec, "confidence", 1.0)

                rule_human_name = getattr(rec, "title", EKB_RULE_NAMES.get(rec.rule_id, rec.rule_id))

                findings_comparison.append({
                    "rule_id": rec.rule_id,
                    "rule_name": rule_human_name,
                    "category": str(getattr(rec, "category", "Code Structure")),
                    "line_number": f_line,
                    "confidence_before": round(conf_before, 2),
                    "confidence_after": round(confidence_after, 2),
                    "is_resolved": is_resolved
                })

            structural_changes_summary = []
            for fix in transform_res.auto_applied_fixes:
                structural_changes_summary.append(f"[{fix.get('rule_id')}] {fix.get('description')}")
            if not structural_changes_summary:
                structural_changes_summary.append(
                    "No modeled improvement: generated automatic changes were withheld."
                    if no_modeled_improvement else "No loop-invariant AST transformations were required."
                )

            carbon_source = str(getattr(carbon_result.carbon_data, "source", "Electricity Maps"))
            estimation_method = str(getattr(carbon_result.carbon_data, "estimation_method", ""))
            if carbon_result.fallback_used:
                carbon_source_type = "fallback"
            elif "mock" in carbon_source.lower() or "mock" in estimation_method.lower():
                carbon_source_type = "mock"
            else:
                carbon_source_type = "live"

            carbon_metadata = {
                "zone": zone,
                "carbon_intensity": round(intensity, 2),
                "is_mock": carbon_source_type == "mock",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": carbon_source,
                "source_type": carbon_source_type,
            }

            smells_before = len([f for f in smell_report.findings if getattr(f.confidence, "value", 0.0) >= 0.5])
            smells_after = len([f for f in smell_report_after.findings if getattr(f.confidence, "value", 0.0) >= 0.5])
            rule_count_before = len({finding.rule_id for finding in smell_report.findings})
            rule_count_after = len({finding.rule_id for finding in smell_report_after.findings})
            finding_locations_before = len(smell_report.findings)
            finding_locations_after = len(smell_report_after.findings)
            resolved_rule_count = len(
                {finding.rule_id for finding in smell_report.findings}
                - {finding.rule_id for finding in smell_report_after.findings}
            )
            smell_burden_before = round(sum(getattr(f.confidence, "value", 0.0) for f in smell_report.findings), 2)
            smell_burden_after = round(sum(getattr(f.confidence, "value", 0.0) for f in smell_report_after.findings), 2)

            ess_reduction = round(((ess - ess_after) / ess) * 100.0, 1) if ess > 0 else 0.0
            cirs_reduction = round(((cirs_before - cirs_after) / cirs_before) * 100.0, 1) if cirs_before > 0 else 0.0
            energy_reduction = round(((energy_joules_before - energy_joules_after) / energy_joules_before) * 100.0, 1) if energy_joules_before > 0 else 0.0
            carbon_reduction = round(((hazard_before - hazard_after) / hazard_before) * 100.0, 1) if hazard_before > 0 else 0.0
            smells_resolved = max(0, smells_before - smells_after)

            real_estimated_impact = {
                "ess_reduction_percent": ess_reduction,
                "cirs_reduction_percent": cirs_reduction,
                "energy_saving_percent": energy_reduction,
                "carbon_saving_percent": carbon_reduction,
                "smells_resolved": smells_resolved,
                "no_modeled_improvement": no_modeled_improvement,
                "fix_status": fix_status,
                "fix_reason": fix_reason,
            }

            post_refactor_estimation = {
                "fix_status": fix_status,
                "fix_reason": fix_reason,
                "auto_fix_candidate_count": auto_fix_candidate_count,
                "cirs_before": round(cirs_before, 9),
                "cirs_after": round(cirs_after, 9),
                "ess_before": round(ess, 6),
                "ess_after": round(ess_after, 6),
                "sci_before": round(sci_before, 4),
                "sci_after": round(sci_after, 4),
                "complexity_before": {
                    "cc": getattr(result["complexity_metrics"], "cyclomatic_complexity", 1.0),
                    "nd": getattr(result["complexity_metrics"], "max_nesting_depth", 1.0),
                    "fd": getattr(result["complexity_metrics"], "function_density", 1.0),
                    "sci": round(sci_before, 4)
                },
                "complexity_after": {
                    "cc": getattr(complexity_metrics_after, "cyclomatic_complexity", 1.0),
                    "nd": getattr(complexity_metrics_after, "max_nesting_depth", 1.0),
                    "fd": round(fd_after, 4),
                    "sci": round(sci_after, 4)
                },
                "structural_trace": structural_trace,
                "energy_before_joules": round(energy_joules_before, 4),
                "energy_after_joules": round(energy_joules_after, 4),
                "energy_before_kwh": round(energy_kwh_before, 8),
                "energy_after_kwh": round(energy_kwh_after, 8),
                "hazard_before": round(hazard_before, 6),
                "hazard_after": round(hazard_after, 6),
                "exposure_before": round(exposure_before, 4),
                "exposure_after": round(exposure_after, 4),
                "predicted_reduction_percent": predicted_reduction_percent,
                "measured_reduction_percent": measured_reduction_percent,
                "smells_before": smells_before,
                "smells_after": smells_after,
                "rule_count_before": rule_count_before,
                "rule_count_after": rule_count_after,
                "resolved_rule_count": resolved_rule_count,
                "finding_locations_before": finding_locations_before,
                "finding_locations_after": finding_locations_after,
                "smell_burden_before": smell_burden_before,
                "smell_burden_after": smell_burden_after,
                "measurement_reliability": measured_runtime.get("measurement_reliability", "reliable"),
                "reliability_threshold_ms": measured_runtime.get("reliability_threshold_ms", 50.0),
                "reliability_note": measured_runtime.get("reliability_note", ""),
                "metric_changes": metric_changes,
                "stage_timings_sec": stage_timings_sec,
                "no_modeled_improvement": no_modeled_improvement,
                "model_interpretation": (
                    "Modeled energy combines structural complexity with a loop-weighted "
                    "operation estimate. Iteration counts are assumed, so this is a static "
                    "comparison rather than a direct power measurement."
                ),
                "findings_comparison": findings_comparison,
                "structural_changes_summary": structural_changes_summary,
                "measured_runtime": measured_runtime,
                "carbon_metadata": carbon_metadata
            }

            raw_base = Path(filename).name
            stem = raw_base[:-3] if raw_base.lower().endswith(".py") else raw_base
            opt_filename = f"{stem}_optimized.py"
            persistent_opt_path = workspace_temp_dir / opt_filename
            with open(persistent_opt_path, "w", encoding="utf-8") as f:
                f.write(transform_res.optimized_code)
            optimized_file_url = f"/download-optimized/{opt_filename}"

        finally:
            if temp_opt_path.exists():
                try:
                    temp_opt_path.unlink()
                except Exception:
                    pass

        location_suggestions = build_location_suggestions(
            source_code,
            serialize_value(result).get("energy_smell_report", {}).get("findings", []),
            transform_res.auto_applied_fixes,
            analyzer=lambda rewritten: [
                {"rule_id": finding.rule_id, "confidence": float(getattr(finding.confidence, "value", 1.0) if hasattr(finding, "confidence") else 1.0)}
                for finding in pipeline._detect(
                    pipeline._analysis_engine.analyze_source(rewritten, temp_path)
                ).findings
            ],
        )
        response = {
            "filename": filename,
            "original_code": source_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pipeline_raw": serialize_value(result),
            "research_metrics": {
                "energy_smell_score": ess,
                "carbon_impact_risk_score": cirs_research,
                "ess_version": "1.0.0-prototype",
                "cirs_version": "1.0.0-prototype",
            },
            "recommendations": serialize_value(recommendation_report),
            "optimized_code": transform_res.optimized_code,
            "optimized_file_url": optimized_file_url,
            "auto_applied_fixes": transform_res.auto_applied_fixes,
            "manual_fixes": transform_res.manual_fixes,
            "location_suggestions": location_suggestions,
            "ai_suggestions_unavailable": any(item["ai_unavailable"] for item in location_suggestions),
            "estimated_impact": real_estimated_impact,
            "measured_runtime": measured_runtime,
            "execution_status": measured_runtime.get("execution_status", "not_executed"),
            "post_refactor_estimation": post_refactor_estimation,
            **footprint_comparison,
            "cirs_before": round(cirs_before, 9),
            "cirs_after": round(cirs_after, 9),
            "window_start": window_start,
            "window_end": window_end,
            "green_window_intensity": round(best_intensity, 2),
        }

        return response

    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass


@router.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_file(
    file: UploadFile = File(...),
    zone: str = Form("DK-DK1"),
    use_global_average: bool = Form(True)
) -> dict[str, Any]:
    """
    Upload a Python source file to execute static analysis, carbon estimation, AST transformation, and sandboxed measurement.
    """
    if not file.filename or not file.filename.lower().endswith(".py"):
        raise HTTPException(status_code=400, detail="Only Python (.py) source files are supported.")

    content_bytes = await file.read()
    if len(content_bytes) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File size exceeds maximum allowed limit of 2 MB.")

    try:
        source_code = content_bytes.decode("utf-8", errors="replace")
        try:
            ast.parse(source_code, filename=file.filename)
        except SyntaxError as se:
            raise HTTPException(status_code=400, detail=f"Python syntax error: {se}")
        # The analysis pipeline performs CPU-heavy AST work and starts sandbox
        # subprocesses. Keep it off the event loop so the API can continue
        # serving requests while an uploaded file is being analyzed.
        return await run_in_threadpool(
            run_single_file_analysis,
            file.filename,
            source_code,
            zone=zone,
            use_global_average=use_global_average,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def run_project_analysis(
    items_to_analyze: list[tuple[str, bytes]],
    project_name: str,
    zone: str,
    use_global_average: bool,
    start_time: float,
) -> dict[str, Any]:
    if not items_to_analyze:
        return {
            "project_name": project_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_files": 0,
            "successful_files": 0,
            "error_files": 0,
            "total_lines_of_code": 0,
            "total_rule_count": 0,
            "total_findings": 0,
            "avg_sci": 0.0,
            "avg_ess": 0.0,
            "avg_cirs": 0.0,
            "total_cirs": 0.0,
            "total_energy_joules": 0.0,
            "total_energy_kwh": 0.0,
            "project_before": {"energy": 0.0, "cirs": 0.0, "ess": 0.0},
            "project_after": {"energy": 0.0, "cirs": 0.0, "ess": 0.0},
            "project_delta": {"energy": 0.0, "cirs": 0.0, "ess": 0.0},
            "project_delta_percent": {"energy": 0.0, "cirs": 0.0, "ess": 0.0},
            "scheduling": {"status": "unavailable", "error": "No successfully analyzed files were available to schedule."},
            "auto_fixable_count": 0,
            "auto_applied_count": 0,
            "total_analysis_time_sec": round(time.time() - start_time, 3),
            "files": []
        }

    def analyze_project_file(item: tuple[str, bytes]) -> dict[str, Any]:
        rel_path, c_bytes = item
        f_start = time.time()
        filename_only = Path(rel_path).name
        code_str = c_bytes.decode("utf-8", errors="replace")
        loc = len([line for line in code_str.splitlines() if line.strip()])

        try:
            res_dict = run_single_file_analysis(
                filename_only,
                code_str,
                zone=zone,
                use_global_average=use_global_average,
                measure_runtime=False,
            )
            f_time = round(time.time() - f_start, 3)

            f_sci = res_dict["post_refactor_estimation"]["sci_before"]
            # Match the file row to the same Radon SLOC field shown on File Results.
            f_loc = int(res_dict.get("pipeline_raw", {}).get("complexity_metrics", {}).get("lines_of_code", loc))
            post = res_dict["post_refactor_estimation"]
            f_ess = float(post.get("ess_before", res_dict["research_metrics"]["energy_smell_score"]))
            f_cirs = float(post.get("cirs_before", res_dict["research_metrics"]["carbon_impact_risk_score"]))
            f_joules = float(post["energy_before_joules"])
            f_energy_after = float(post.get("energy_after_joules", f_joules))
            f_cirs_after = float(post.get("cirs_after", f_cirs))
            f_ess_after = float(post.get("ess_after", f_ess))
            fix_status = post.get("fix_status", "applied" if res_dict.get("auto_applied_fixes") else "not_auto_fixable")
            fix_reason = post.get("fix_reason") or (
                "An automatic AST fix was retained." if fix_status == "applied"
                else "No safe automatic AST transformation was available for this file."
            )
            file_auto_fixable_count = int(post.get(
                "auto_fix_candidate_count",
                1 if fix_status != "not_auto_fixable" else 0,
            ))
            file_auto_applied_count = len(res_dict.get("auto_applied_fixes", []))
            raw_findings = res_dict.get("pipeline_raw", {}).get("energy_smell_report", {}).get("findings", [])
            f_rules = len({item.get("rule_id") for item in raw_findings if isinstance(item, dict) and item.get("rule_id")})
            # Finding locations are the single shared count definition across
            # project, file, and impact views. Recommendations/rule IDs are not
            # substitutes for detector locations.
            f_findings = len(raw_findings)

            return {
                "filename": filename_only,
                "relative_path": rel_path,
                "lines_of_code": f_loc,
                "status": "success",
                "error_message": None,
                "original_code": code_str,
                "findings_count": f_findings,
                "rule_count": f_rules,
                "sci": round(f_sci, 4),
                "ess": round(f_ess, 2),
                "cirs": round(f_cirs, 6),
                "energy_joules": round(f_joules, 4),
                "before_energy": round(float(f_joules), 4),
                "after_energy": round(f_energy_after, 4),
                "before_cirs": round(float(f_cirs), 9),
                "after_cirs": round(f_cirs_after, 9),
                "before_ess": round(float(f_ess), 6),
                "after_ess": round(f_ess_after, 6),
                "fix_status": fix_status,
                "fix_reason": fix_reason,
                "auto_fixable_count": file_auto_fixable_count,
                "auto_applied_count": file_auto_applied_count,
                "analysis_time_sec": f_time,
                "single_file_response": res_dict
            }
        except Exception as exc:
            f_time = round(time.time() - f_start, 3)
            return {
                "filename": filename_only,
                "relative_path": rel_path,
                "lines_of_code": loc,
                "status": "error",
                "error_message": str(exc),
                "findings_count": 0,
                "rule_count": 0,
                "sci": 0.0,
                "ess": 0.0,
                "cirs": 0.0,
                "energy_joules": 0.0,
                "before_energy": 0.0,
                "after_energy": 0.0,
                "before_cirs": 0.0,
                "after_cirs": 0.0,
                "before_ess": 0.0,
                "after_ess": 0.0,
                "fix_status": "not_auto_fixable",
                "fix_reason": "Analysis failed; no automatic fix was evaluated.",
                "auto_fixable_count": 0,
                "auto_applied_count": 0,
                "analysis_time_sec": f_time,
                "single_file_response": None
            }

    # Keep project uploads bounded in time. Each file is independent, and the
    # stable map order preserves the archive's file order in the response.
    worker_count = min(4, len(items_to_analyze))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        file_results = list(executor.map(analyze_project_file, items_to_analyze))

    successful_results = [item for item in file_results if item["status"] == "success"]
    success_count = len(successful_results)
    error_count = len(file_results) - success_count
    sci_list = [item["sci"] for item in successful_results]
    ess_list = [item["ess"] for item in successful_results]
    cirs_list = [item["cirs"] for item in successful_results]
    total_joules = sum(item["energy_joules"] for item in successful_results)
    total_loc = sum(item["lines_of_code"] for item in file_results)
    total_findings = sum(item["findings_count"] for item in successful_results)
    total_rule_count = sum(item["rule_count"] for item in successful_results)

    total_time = round(time.time() - start_time, 3)
    avg_sci = round(sum(sci_list) / len(sci_list), 4) if sci_list else 0.0
    avg_ess = round(sum(ess_list) / len(ess_list), 2) if ess_list else 0.0
    avg_cirs = round(sum(cirs_list) / len(cirs_list), 6) if cirs_list else 0.0
    total_cirs = round(sum(cirs_list), 6) if cirs_list else 0.0
    project_before = {
        "energy": round(sum(float(item["before_energy"]) for item in successful_results), 4),
        "cirs": round(sum(float(item["before_cirs"]) for item in successful_results), 9),
        "ess": round(sum(float(item["before_ess"]) for item in successful_results), 6),
    }
    project_after = {
        "energy": round(sum(float(item["after_energy"]) for item in successful_results), 4),
        "cirs": round(sum(float(item["after_cirs"]) for item in successful_results), 9),
        "ess": round(sum(float(item["after_ess"]) for item in successful_results), 6),
    }
    project_delta = {key: round(project_after[key] - project_before[key], 9) for key in project_before}
    project_delta_percent = {
        key: round(project_delta[key] / project_before[key] * 100.0, 4) if project_before[key] else 0.0
        for key in project_before
    }
    auto_fixable_count = sum(item["auto_fixable_count"] for item in successful_results)
    auto_applied_count = sum(item["auto_applied_count"] for item in successful_results)
    carbon_reference = next(
        (item.get("single_file_response", {}).get("post_refactor_estimation", {}).get("carbon_metadata")
         for item in successful_results if item.get("single_file_response")),
        None,
    )
    try:
        scheduling = build_project_scheduling(
            zone,
            project_after["energy"],
            float(carbon_reference.get("carbon_intensity", 0.0)) if carbon_reference else 0.0,
            carbon_reference.get("source") if carbon_reference else None,
            carbon_reference.get("source_type") if carbon_reference else None,
        )
    except Exception as exc:
        scheduling = {"status": "unavailable", "error": str(exc), "source": "Unknown", "source_type": "unknown"}

    return {
        "project_name": project_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_files": len(items_to_analyze),
        "successful_files": success_count,
        "error_files": error_count,
        "total_lines_of_code": total_loc,
        "total_rule_count": total_rule_count,
        "total_findings": total_findings,
        "avg_sci": avg_sci,
        "avg_ess": avg_ess,
        "avg_cirs": avg_cirs,
        "total_cirs": total_cirs,
        "total_energy_joules": round(total_joules, 4),
        "total_energy_kwh": round(total_joules / 3_600_000.0, 8),
        "project_before": project_before,
        "project_after": project_after,
        "project_delta": project_delta,
        "project_delta_percent": project_delta_percent,
        "auto_fixable_count": auto_fixable_count,
        "auto_applied_count": auto_applied_count,
        "total_analysis_time_sec": total_time,
        "carbon_intensity": carbon_reference.get("carbon_intensity") if carbon_reference else None,
        "carbon_zone": carbon_reference.get("zone") if carbon_reference else None,
        "carbon_source": carbon_reference.get("source") if carbon_reference else None,
        "carbon_source_type": carbon_reference.get("source_type") if carbon_reference else None,
        "scheduling": scheduling,
        "files": file_results
    }


@router.post("/analyze-project", response_model=ProjectAnalyzeResponse, tags=["Analysis"])
@router.post("/analyze-zip", response_model=ProjectAnalyzeResponse, tags=["Analysis"])
async def analyze_project(
    files: list[UploadFile] = File(None),
    file: UploadFile = File(None),
    zone: str = Form("DK-DK1"),
    use_global_average: bool = Form(True)
) -> dict[str, Any]:
    """
    Upload an entire Python project (ZIP archive or multiple .py files).
    Executes static analysis, EKB detection, SCI/ESS/CIRS, AST transformer, and sandbox timings across files.
    Calculates macro-average SCI & ESS, primary Average Per-File CIRS, secondary Total Summed CIRS, and per-file breakdowns.
    """
    start_time = time.time()
    items_to_analyze: list[tuple[str, bytes]] = []
    project_name = "Python Project"

    if file is not None and file.filename:
        project_name = file.filename
        content_bytes = await file.read()
        if file.filename.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(content_bytes)) as zf:
                    for zip_info in zf.infolist():
                        if zip_info.is_dir():
                            continue
                        name = zip_info.filename
                        parts = Path(name).parts
                        if any(p.startswith(".") or p in ("__pycache__", "venv", "env", "node_modules", "dist", "build", "temp_analysis", "scratch", ".pytest_cache") for p in parts):
                            continue
                        if name.lower().endswith(".py"):
                            file_data = zf.read(zip_info)
                            items_to_analyze.append((name, file_data))
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to extract ZIP archive: {str(e)}")
        elif file.filename.lower().endswith(".py"):
            items_to_analyze.append((file.filename, content_bytes))
        else:
            raise HTTPException(status_code=400, detail="Uploaded file must be a .zip archive or a .py source file.")

    if files:
        for f in files:
            if f.filename and f.filename.lower().endswith(".py"):
                c_bytes = await f.read()
                clean_path = f.filename.replace("\\", "/")
                items_to_analyze.append((clean_path, c_bytes))

    return await run_in_threadpool(
        run_project_analysis,
        items_to_analyze,
        project_name,
        zone,
        use_global_average,
        start_time,
    )

@router.get("/download-optimized/{file_name}", tags=["Analysis"])
def download_optimized_file(file_name: str) -> FileResponse:
    """
    Download the refactored/optimized Python source file generated during analysis.
    """
    workspace_temp_dir = Path("temp_analysis")
    safe_filename = Path(file_name).name
    file_path = workspace_temp_dir / safe_filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Optimized file not found.")

    return FileResponse(
        path=str(file_path),
        filename=safe_filename,
        media_type="text/x-python",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'}
    )


def build_forecast_response(zone: str, energy_joules: float) -> dict[str, Any]:
    pipeline = PredictivePipeline()
    dummy_energy = EnergyResult(
        runtime=RuntimeEstimate(runtime=0.1),
        energy=EnergyEstimate(energy_joules=energy_joules)
    )
    forecasts = pipeline._carbon_engine.forecast(dummy_energy, zone=zone)
    if not forecasts:
        raise ValueError("Forecast provider returned no data")

    current = forecasts[0]
    best = pipeline._carbon_engine.best_execution_window(forecasts)
    reduction = pipeline._carbon_engine.percentage_reduction(current, best)
    source = str(getattr(best.carbon_data, "source", "Unknown"))
    estimation_method = str(getattr(best.carbon_data, "estimation_method", ""))
    if best.fallback_used:
        source_type = "fallback"
    elif "mock" in source.lower() or "mock" in estimation_method.lower():
        source_type = "mock"
    elif getattr(best.carbon_data, "is_estimated", False):
        source_type = "fallback"
    else:
        source_type = "live"
    hourly_series = [{
        "timestamp": item.carbon_data.timestamp.isoformat(),
        "carbon_intensity": round(item.carbon_data.carbon_intensity, 2),
        "emissions_g": round(item.carbon.carbon_grams, 6),
    } for item in forecasts]
    return {
        "zone": zone,
        "current_carbon_intensity": round(current.carbon_data.carbon_intensity, 2),
        "lowest_forecast_intensity": round(best.carbon_data.carbon_intensity, 2),
        "percentage_reduction": round(reduction, 2),
        "recommended_execution_time": best.carbon_data.timestamp.isoformat(),
        "hourly_forecasts": hourly_series,
        "source": source,
        "source_type": source_type,
    }


def build_project_scheduling(
    zone: str,
    energy_joules: float,
    intensity_now: float,
    current_source: str | None,
    current_source_type: str | None,
) -> dict[str, Any]:
    forecast = build_forecast_response(zone, energy_joules)
    forecast_minimum = float(forecast["lowest_forecast_intensity"])
    has_cleaner_window = forecast_minimum < intensity_now if intensity_now > 0 else False
    intensity_window = forecast_minimum if has_cleaner_window else intensity_now
    start = datetime.fromisoformat(forecast["recommended_execution_time"])
    return {
        **forecast,
        "status": "available",
        "source": current_source or forecast["source"],
        "source_type": current_source_type or forecast["source_type"],
        "window_start": start.isoformat() if has_cleaner_window else None,
        "window_end": (start + timedelta(hours=1)).isoformat() if has_cleaner_window else None,
        "intensity_now": intensity_now,
        "forecast_minimum_intensity": forecast_minimum,
        "intensity_window": intensity_window,
        "has_cleaner_window": has_cleaner_window,
        "scheduling_reduction_percent": round(
            max(0.0, (intensity_now - intensity_window) / intensity_now * 100.0), 2
        ) if intensity_now > 0 else 0.0,
    }


@router.get("/forecast", response_model=ForecastResponse, tags=["Scheduling"])
def get_forecast(
    zone: str = Query("DK-DK1", description="Grid zone ID"),
    energy_joules: float = Query(100.0, description="Energy consumption in Joules")
) -> dict[str, Any]:
    """Expose carbon window scheduling logic and forecast hourly emissions."""
    try:
        return build_forecast_response(zone, energy_joules)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# Register router for both root paths and /api prefix paths
app.include_router(router)
app.include_router(router, prefix="/api")

# Mount static frontend files if dashboard/dist exists
dashboard_dist = Path(__file__).resolve().parent.parent.parent / "dashboard" / "dist"
if dashboard_dist.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(dashboard_dist), html=True), name="static")

