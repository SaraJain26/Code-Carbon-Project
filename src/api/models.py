"""
FastAPI Request/Response schemas.
"""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="API service health status")


class ResearchMetricsSchema(BaseModel):
    energy_smell_score: float = Field(..., description="Fuzzy union score with one capped contribution per distinct rule ID")
    carbon_impact_risk_score: float = Field(..., description="Risk-weighted CIRS research score; not the unweighted physical carbon footprint")
    ess_version: str = Field(..., description="Version of the ESS calculation model")
    cirs_version: str = Field(..., description="Version of the CIRS calculation model")


class ComplexityMetricsDetail(BaseModel):
    cc: float = Field(..., description="Cyclomatic Complexity")
    nd: float = Field(..., description="Max Nesting Depth")
    fd: float = Field(..., description="Function Density")
    sci: float = Field(..., description="Structural Complexity Index")


class FindingComparisonItem(BaseModel):
    rule_id: str = Field(..., description="EKB Rule ID")
    rule_name: str = Field(..., description="EKB Rule Name")
    category: str = Field(..., description="Rule category")
    line_number: int | None = Field(None, description="Line number of finding")
    confidence_before: float = Field(..., description="Confidence score before refactoring")
    confidence_after: float = Field(..., description="Confidence score after refactoring")
    is_resolved: bool = Field(..., description="Whether the smell was resolved after AST transformation")


class CarbonMetadataDetail(BaseModel):
    zone: str = Field(..., description="Grid zone ID")
    carbon_intensity: float = Field(..., description="Carbon intensity in gCO2eq/kWh")
    is_mock: bool = Field(..., description="Whether mock provider fallback was used")
    timestamp: str = Field(..., description="Timestamp of carbon intensity reading")
    source: str = Field(..., description="Carbon intensity provider source")
    source_type: str = Field(..., description="Whether intensity is live, fallback, or mock data")


class PostRefactorEstimation(BaseModel):
    cirs_before: float = Field(..., description="Unitless risk-weighted CIRS research score before refactoring")
    cirs_after: float = Field(..., description="Unitless risk-weighted CIRS research score after refactoring")
    ess_before: float = Field(..., description="Energy Smell Score before refactoring")
    ess_after: float = Field(..., description="Energy Smell Score after refactoring")
    sci_before: float = Field(..., description="Structural Complexity Index before refactoring")
    sci_after: float = Field(..., description="Structural Complexity Index after refactoring")
    complexity_before: ComplexityMetricsDetail = Field(..., description="Complexity metrics breakdown before")
    complexity_after: ComplexityMetricsDetail = Field(..., description="Complexity metrics breakdown after")
    energy_before_joules: float = Field(..., description="Relative modeled energy score before (reported in modeled J)")
    energy_after_joules: float = Field(..., description="Relative modeled energy score after (reported in modeled J)")
    energy_before_kwh: float = Field(..., description="Energy consumption in kWh before")
    energy_after_kwh: float = Field(..., description="Energy consumption in kWh after")
    hazard_before: float = Field(..., description="Environmental hazard before")
    hazard_after: float = Field(..., description="Environmental hazard after")
    exposure_before: float = Field(..., description="Environmental risk exposure before")
    exposure_after: float = Field(..., description="Environmental risk exposure after")
    predicted_reduction_percent: float = Field(..., description="Model-based predicted CIRS reduction percentage")
    measured_reduction_percent: float = Field(..., description="Empirical sandboxed runtime measured reduction percentage")
    findings_comparison: list[FindingComparisonItem] = Field(default_factory=list, description="Comparison of EKB findings before vs after")
    structural_changes_summary: list[str] = Field(default_factory=list, description="Summary of traceable structural changes")
    measured_runtime: dict[str, Any] = Field(default_factory=dict, description="Detailed empirical sandboxed runtime comparison")
    carbon_metadata: CarbonMetadataDetail = Field(..., description="Metadata on carbon grid intensity lookup")
    smells_before: int = Field(0, description="Count of findings with confidence >= 0.5 before refactor")
    smells_after: int = Field(0, description="Count of findings with confidence >= 0.5 after refactor")
    smell_burden_before: float = Field(0.0, description="Sum of finding confidences before refactor")
    smell_burden_after: float = Field(0.0, description="Sum of finding confidences after refactor")


class AnalyzeResponse(BaseModel):
    filename: str = Field(..., description="Name of the analyzed file")
    original_code: str | None = Field(None, description="Original uploaded Python source, preserved for source-based fix display")
    timestamp: str = Field(..., description="ISO 8601 timestamp of when the analysis occurred")
    pipeline_raw: dict[str, Any] = Field(..., description="Raw pipeline execution results")
    research_metrics: ResearchMetricsSchema = Field(..., description="Experimental Version 1 research metrics")
    recommendations: dict[str, Any] = Field(..., description="Prioritized optimization recommendations")
    optimized_code: str = Field(default="", description="Transformed Python source code with automated refactoring")
    auto_applied_fixes: list[dict[str, Any]] = Field(default_factory=list, description="Automated AST fixes applied")
    manual_fixes: list[dict[str, Any]] = Field(default_factory=list, description="Manual fixes required per recommendation")
    estimated_impact: dict[str, Any] = Field(default_factory=dict, description="Modeled before/after impact estimate")
    measured_runtime: dict[str, Any] = Field(default_factory=dict, description="Empirical sandboxed runtime measurement")
    post_refactor_estimation: dict[str, Any] = Field(default_factory=dict, description="Comprehensive post-recommendation estimation breakdown")
    carbon_before: float = Field(..., description="Unweighted modeled carbon footprint in gCO2eq/run before changes")
    carbon_after_now: float = Field(..., description="Unweighted modeled carbon footprint in gCO2eq/run after changes at current intensity")
    carbon_after_green: float = Field(..., description="Unweighted modeled carbon footprint in gCO2eq/run after changes at forecast intensity")
    cirs_before: float = Field(..., description="Unitless risk-weighted CIRS research score before changes")
    cirs_after: float = Field(..., description="Unitless risk-weighted CIRS research score after changes")
    execution_status: str = Field("not_executed", description="Whether uploaded code was executed; static analysis is the default")
    window_start: str | None = Field(None, description="Start timestamp of best forecast execution window")
    window_end: str | None = Field(None, description="End timestamp of best forecast execution window")
    code_only_pct: float = Field(..., description="Percent reduction in unweighted modeled gCO2eq/run from code changes at current intensity")
    schedule_only_pct: float = Field(..., description="Percent reduction in unweighted modeled gCO2eq/run from current to forecast intensity")
    total_pct: float = Field(..., description="Percent reduction in unweighted modeled gCO2eq/run from original code now to changed code in the forecast window")
    green_window_intensity: float = Field(..., description="Best forecast carbon intensity in gCO2eq/kWh")
    optimized_file_url: str | None = Field(None, description="URL endpoint to download the refactored optimized source file")


class ProjectFileResult(BaseModel):
    filename: str = Field(..., description="Name of the file")
    relative_path: str = Field(..., description="Relative path in project")
    original_code: str | None = Field(None, description="Original uploaded Python source, preserved for source-based fix display")
    lines_of_code: int = Field(0, description="Lines of code in file")
    status: str = Field("success", description="Analysis status: success or error")
    execution_status: str = Field("not_executed", description="Whether source code was run by the measurement sandbox")
    error_message: str | None = Field(None, description="Error message if analysis failed")
    rule_count: int = Field(0, description="Number of distinct detected smell rules in this file")
    findings_count: int = Field(0, description="Number of detector finding locations in this file")
    sci: float = Field(0.0, description="Structural Complexity Index")
    ess: float = Field(0.0, description="Energy Smell Score")
    cirs: float = Field(0.0, description="Carbon Impact Risk Score")
    energy_joules: float = Field(0.0, description="Relative modeled energy score, reported in modeled J")
    before_energy: float = Field(0.0, description="Estimated energy before automatic refactoring")
    after_energy: float = Field(0.0, description="Estimated energy after accepted automatic refactoring")
    before_cirs: float = Field(0.0, description="Summed unitless CIRS before automatic refactoring")
    after_cirs: float = Field(0.0, description="Summed unitless CIRS after accepted automatic refactoring")
    before_ess: float = Field(0.0, description="ESS before automatic refactoring")
    after_ess: float = Field(0.0, description="ESS after accepted automatic refactoring")
    fix_status: Literal["applied", "rejected_no_improvement", "rejected_regression", "not_auto_fixable"] = Field(
        "not_auto_fixable", description="Automatic fix status"
    )
    fix_reason: str = Field("", description="Reason the automatic fix was or was not retained")
    auto_fixable_count: int = Field(0, description="Automatic transformation candidates generated for this file")
    auto_applied_count: int = Field(0, description="Automatic transformations retained for this file")
    analysis_time_sec: float = Field(0.0, description="Analysis duration in seconds")
    single_file_response: dict[str, Any] | None = Field(None, description="Full single-file analyze response")


class ProjectAnalyzeResponse(BaseModel):
    project_name: str = Field(..., description="Name of the uploaded project / archive")
    timestamp: str = Field(..., description="ISO 8601 timestamp of analysis execution")
    total_files: int = Field(..., description="Total number of .py files found in project")
    successful_files: int = Field(..., description="Number of successfully analyzed files")
    error_files: int = Field(..., description="Number of files that failed analysis")
    total_lines_of_code: int = Field(..., description="Total lines of Python code across project")
    total_rule_count: int = Field(0, description="Sum of per-file distinct rule counts")
    total_findings: int = Field(..., description="Total detector finding locations across all files")
    avg_sci: float = Field(..., description="Primary metric: Macro-average Structural Complexity Index")
    avg_ess: float = Field(..., description="Primary metric: Macro-average Energy Smell Score")
    avg_cirs: float = Field(..., description="Mean per-file risk-weighted carbon score; not an unweighted carbon footprint")
    total_cirs: float = Field(..., description="Sum of per-file risk-weighted scores, assuming one run per file")
    total_energy_joules: float = Field(..., description="Sum of per-file relative energy scores, assuming one run per file")
    total_energy_kwh: float = Field(..., description="kWh-equivalent derived from relative energy scores; not metered energy")
    project_before: dict[str, float] = Field(default_factory=dict, description="Summed estimated energy, CIRS, and ESS before refactoring")
    project_after: dict[str, float] = Field(default_factory=dict, description="Summed estimated energy, CIRS, and ESS after accepted refactoring")
    project_delta: dict[str, float] = Field(default_factory=dict, description="Absolute after-minus-before deltas")
    project_delta_percent: dict[str, float] = Field(default_factory=dict, description="After-minus-before percentage deltas")
    auto_fixable_count: int = Field(0, description="Files with a generated automatic transformation candidate")
    auto_applied_count: int = Field(0, description="Files with an accepted automatic transformation")
    total_analysis_time_sec: float = Field(..., description="Total project analysis time in seconds")
    carbon_intensity: float | None = Field(None, description="Carbon intensity used for project footprint estimate")
    carbon_zone: str | None = Field(None, description="Grid zone used for project footprint estimate")
    carbon_source: str | None = Field(None, description="Provider source for project carbon intensity")
    carbon_source_type: str | None = Field(None, description="Whether project carbon intensity is live, fallback, or mock data")
    scheduling: dict[str, Any] = Field(default_factory=dict, description="Modeled green scheduling window and provider metadata")
    files: list[ProjectFileResult] = Field(default_factory=list, description="Per-file detailed breakdown")


class ForecastResponse(BaseModel):
    zone: str = Field(..., description="Grid zone key")
    current_carbon_intensity: float = Field(..., description="Current carbon intensity in gCO2eq/kWh")
    lowest_forecast_intensity: float = Field(..., description="Lowest carbon intensity forecast in gCO2eq/kWh")
    percentage_reduction: float = Field(..., description="Percentage carbon reduction expected")
    recommended_execution_time: str | None = Field(..., description="ISO 8601 timestamp of best forecast window, if available")
    hourly_forecasts: list[dict[str, Any]] = Field(..., description="Hourly forecast data points")
    source: str = Field("Unknown", description="Carbon intensity provider for the forecast")
    source_type: str = Field("unknown", description="Whether forecast intensity is live, fallback, or mock data")
    status: Literal["available", "unavailable"] | None = None
    error: str | None = None
    window_start: str | None = None
    window_end: str | None = None
    intensity_now: float | None = None
    forecast_minimum_intensity: float | None = None
    intensity_window: float | None = None
    has_cleaner_window: bool | None = None
    scheduling_reduction_percent: float | None = None


