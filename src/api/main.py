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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SRC_DIR = Path(__file__).resolve().parent.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

logger = logging.getLogger("codecarbon.api")

import ast
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query, APIRouter
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from carbon import get_carbon_provider, MockCarbonIntensityProvider
from pipeline import PredictivePipeline
from recommendation.engine import RecommendationEngine
from recommendation.transformer import ASTCodeTransformer
from energy.sandbox import SandboxedRuntimeExecutor
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
    try:
        ast.parse(source_code, filename=filename)
    except SyntaxError as se:
        raise HTTPException(status_code=400, detail=f"Python syntax error: {se}")

    workspace_temp_dir = Path("temp_analysis")
    workspace_temp_dir.mkdir(exist_ok=True)

    temp_path = workspace_temp_dir / f"temp_{datetime.now().timestamp()}_{filename}"

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(source_code)

        pipeline = PredictivePipeline()
        result = pipeline.run(
            source_file=temp_path,
            zone=zone,
            use_global_average=use_global_average
        )

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
        transform_res = transformer.transform(source_code, findings=raw_findings)

        # Automatically execute real measurement in isolated sandboxed subprocesses
        if measure_runtime:
            sandbox_executor = SandboxedRuntimeExecutor(timeout_sec=2.0)
            measured_runtime = sandbox_executor.measure_comparison(
                original_code=source_code,
                optimized_code=transform_res.optimized_code
            )
        else:
            measured_runtime = {
                "is_sandboxed": False,
                "measurement_reliability": "unavailable",
                "reliability_threshold_ms": SandboxedRuntimeExecutor.RELIABILITY_THRESHOLD_MS,
                "reliability_note": (
                    "Runtime timing was skipped for project analysis because files were analyzed concurrently; "
                    "run this file individually for an uncontended timing comparison."
                ),
                "energy_method": "Not measured during concurrent project analysis",
                "measured_savings": {"time_reduction_percent": 0.0, "energy_reduction_percent": 0.0},
            }

        # Post-Recommendation Estimation Logic (Re-run static analysis & EKB on refactored code)
        temp_opt_path = workspace_temp_dir / f"temp_opt_{datetime.now().timestamp()}_{filename}"
        with open(temp_opt_path, "w", encoding="utf-8") as f:
            f.write(transform_res.optimized_code)

        try:
            result_after = pipeline.run(
                source_file=temp_opt_path,
                zone=zone,
                use_global_average=use_global_average
            )

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

            if transform_res.auto_applied_fixes:
                temp_base_path = workspace_temp_dir / f"temp_base_{datetime.now().timestamp()}_{filename}"
                try:
                    baseline_code = ast.unparse(ast.parse(source_code))
                    with open(temp_base_path, "w", encoding="utf-8") as bf:
                        bf.write(baseline_code)

                    result_baseline = pipeline.run(
                        source_file=temp_base_path,
                        zone=zone,
                        use_global_average=use_global_average
                    )

                    sci_baseline = result_baseline["complexity_score"].structural_complexity_index
                    energy_baseline = result_baseline["energy_result"].energy.energy_joules
                    fd_baseline = getattr(result_baseline["complexity_metrics"], "function_density", 0.0)

                    sci_after = max(0.0, sci_before + (sci_after - sci_baseline))
                    energy_joules_after = max(0.0, energy_joules_before + (energy_joules_after - energy_baseline))
                    fd_after = max(0.0, fd_before + (fd_after - fd_baseline))
                    energy_kwh_after = energy_joules_after / 3_600_000.0
                except Exception as exc:
                    logger.warning("Reformatted baseline normalization failed: %s", exc)
                finally:
                    if temp_base_path.exists():
                        try:
                            temp_base_path.unlink()
                        except Exception:
                            pass

            hazard_before = energy_kwh_before * intensity
            hazard_after = energy_kwh_after * intensity

            exposure_before = sci_before * (1.0 + (ess / 10.0))
            exposure_after = sci_after * (1.0 + (ess_after / 10.0))

            cirs_before = hazard_before * exposure_before
            cirs_after = hazard_after * exposure_after

            logger.info(
                f"[CIRS Breakdown] E_kWh: {energy_kwh_before:.8f} -> {energy_kwh_after:.8f} | "
                f"SCI: {sci_before:.4f} -> {sci_after:.4f} | "
                f"Hazard: {hazard_before:.6f} -> {hazard_after:.6f} | "
                f"Exposure: {exposure_before:.4f} -> {exposure_after:.4f} | "
                f"CIRS: {cirs_before:.6f} -> {cirs_after:.6f}"
            )

            predicted_reduction_percent = round(((cirs_before - cirs_after) / cirs_before) * 100.0, 1) if cirs_before > 0 else 0.0
            measured_reduction_percent = measured_runtime.get("measured_savings", {}).get("time_reduction_percent", 0.0)

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
                structural_changes_summary.append("No loop-invariant AST transformations were required.")

            carbon_metadata = {
                "zone": zone,
                "carbon_intensity": round(intensity, 2),
                "is_mock": carbon_result.fallback_used,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": getattr(carbon_result.carbon_data, "source", "ElectricityMaps")
            }

            smells_before = len([f for f in smell_report.findings if getattr(f.confidence, "value", 0.0) >= 0.5])
            smells_after = len([f for f in smell_report_after.findings if getattr(f.confidence, "value", 0.0) >= 0.5])
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
            }

            post_refactor_estimation = {
                "cirs_before": round(cirs_before, 6),
                "cirs_after": round(cirs_after, 6),
                "ess_before": round(ess, 2),
                "ess_after": round(ess_after, 2),
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
                "smell_burden_before": smell_burden_before,
                "smell_burden_after": smell_burden_after,
                "measurement_reliability": measured_runtime.get("measurement_reliability", "reliable"),
                "reliability_threshold_ms": measured_runtime.get("reliability_threshold_ms", 50.0),
                "reliability_note": measured_runtime.get("reliability_note", ""),
                "metric_changes": metric_changes,
                "model_interpretation": (
                    "The static energy estimate is driven by structural complexity. "
                    "A resolved smell that preserves control flow may legitimately leave "
                    "complexity, modelled energy, and carbon risk unchanged."
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
            "estimated_impact": real_estimated_impact,
            "measured_runtime": measured_runtime,
            "post_refactor_estimation": post_refactor_estimation,
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
            "total_findings": 0,
            "avg_sci": 0.0,
            "avg_ess": 0.0,
            "avg_cirs": 0.0,
            "total_cirs": 0.0,
            "total_energy_joules": 0.0,
            "total_energy_kwh": 0.0,
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
            f_ess = res_dict["research_metrics"]["energy_smell_score"]
            f_cirs = res_dict["research_metrics"]["carbon_impact_risk_score"]
            f_joules = res_dict["post_refactor_estimation"]["energy_before_joules"]
            raw_summary = res_dict.get("pipeline_raw", {}).get("energy_smell_report", {}).get("summary", {})
            if "total_findings" in raw_summary:
                f_findings = int(raw_summary["total_findings"])
            else:
                recs = res_dict.get("recommendations", {})
                if isinstance(recs, dict):
                    f_findings = len(recs.get("recommendations", []))
                elif isinstance(recs, list):
                    f_findings = len(recs)
                else:
                    f_findings = 0

            return {
                "filename": filename_only,
                "relative_path": rel_path,
                "lines_of_code": loc,
                "status": "success",
                "error_message": None,
                "original_code": code_str,
                "findings_count": f_findings,
                "sci": round(f_sci, 4),
                "ess": round(f_ess, 2),
                "cirs": round(f_cirs, 6),
                "energy_joules": round(f_joules, 4),
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
                "sci": 0.0,
                "ess": 0.0,
                "cirs": 0.0,
                "energy_joules": 0.0,
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

    total_time = round(time.time() - start_time, 3)
    avg_sci = round(sum(sci_list) / len(sci_list), 4) if sci_list else 0.0
    avg_ess = round(sum(ess_list) / len(ess_list), 2) if ess_list else 0.0
    avg_cirs = round(sum(cirs_list) / len(cirs_list), 6) if cirs_list else 0.0
    total_cirs = round(sum(cirs_list), 6) if cirs_list else 0.0

    return {
        "project_name": project_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_files": len(items_to_analyze),
        "successful_files": success_count,
        "error_files": error_count,
        "total_lines_of_code": total_loc,
        "total_findings": total_findings,
        "avg_sci": avg_sci,
        "avg_ess": avg_ess,
        "avg_cirs": avg_cirs,
        "total_cirs": total_cirs,
        "total_energy_joules": round(total_joules, 4),
        "total_energy_kwh": round(total_joules / 3_600_000.0, 8),
        "total_analysis_time_sec": total_time,
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


@router.get("/forecast", response_model=ForecastResponse, tags=["Scheduling"])
def get_forecast(
    zone: str = Query("DK-DK1", description="Grid zone ID"),
    energy_joules: float = Query(100.0, description="Energy consumption in Joules")
) -> dict[str, Any]:
    """
    Expose carbon window scheduling logic and forecast hourly emissions.
    """
    try:
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

        hourly_series = []
        for f in forecasts:
            hourly_series.append({
                "timestamp": f.carbon_data.timestamp.isoformat(),
                "carbon_intensity": round(f.carbon_data.carbon_intensity, 2),
                "emissions_g": round(f.carbon.carbon_grams, 6)
            })

        return {
            "zone": zone,
            "current_carbon_intensity": round(current.carbon_data.carbon_intensity, 2),
            "lowest_forecast_intensity": round(best.carbon_data.carbon_intensity, 2),
            "percentage_reduction": round(reduction, 2),
            "recommended_execution_time": best.carbon_data.timestamp.isoformat(),
            "hourly_forecasts": hourly_series
        }

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

