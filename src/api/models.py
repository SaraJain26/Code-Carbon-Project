"""
FastAPI Request/Response schemas.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="API service health status")


class ResearchMetricsSchema(BaseModel):
    energy_smell_score: float = Field(..., description="Fuzzy aggregative expected smell count")
    carbon_impact_risk_score: float = Field(..., description="Environmental hazard carbon risk score in grams of CO2eq")
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


class PostRefactorEstimation(BaseModel):
    cirs_before: float = Field(..., description="Carbon Impact Risk Score before refactoring")
    cirs_after: float = Field(..., description="Carbon Impact Risk Score after refactoring")
    ess_before: float = Field(..., description="Energy Smell Score before refactoring")
    ess_after: float = Field(..., description="Energy Smell Score after refactoring")
    sci_before: float = Field(..., description="Structural Complexity Index before refactoring")
    sci_after: float = Field(..., description="Structural Complexity Index after refactoring")
    complexity_before: ComplexityMetricsDetail = Field(..., description="Complexity metrics breakdown before")
    complexity_after: ComplexityMetricsDetail = Field(..., description="Complexity metrics breakdown after")
    energy_before_joules: float = Field(..., description="Energy consumption in Joules before")
    energy_after_joules: float = Field(..., description="Energy consumption in Joules after")
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


class AnalyzeResponse(BaseModel):
    filename: str = Field(..., description="Name of the analyzed file")
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
    optimized_file_url: str | None = Field(None, description="URL endpoint to download the refactored optimized source file")


class ProjectFileResult(BaseModel):
    filename: str = Field(..., description="Name of the file")
    relative_path: str = Field(..., description="Relative path in project")
    lines_of_code: int = Field(0, description="Lines of code in file")
    status: str = Field("success", description="Analysis status: success or error")
    error_message: str | None = Field(None, description="Error message if analysis failed")
    findings_count: int = Field(0, description="Number of energy smells found")
    sci: float = Field(0.0, description="Structural Complexity Index")
    ess: float = Field(0.0, description="Energy Smell Score")
    cirs: float = Field(0.0, description="Carbon Impact Risk Score")
    energy_joules: float = Field(0.0, description="Energy consumption in Joules")
    analysis_time_sec: float = Field(0.0, description="Analysis duration in seconds")
    single_file_response: dict[str, Any] | None = Field(None, description="Full single-file analyze response")


class ProjectAnalyzeResponse(BaseModel):
    project_name: str = Field(..., description="Name of the uploaded project / archive")
    timestamp: str = Field(..., description="ISO 8601 timestamp of analysis execution")
    total_files: int = Field(..., description="Total number of .py files found in project")
    successful_files: int = Field(..., description="Number of successfully analyzed files")
    error_files: int = Field(..., description="Number of files that failed analysis")
    total_lines_of_code: int = Field(..., description="Total lines of Python code across project")
    total_findings: int = Field(..., description="Total energy smells detected across all files")
    avg_sci: float = Field(..., description="Primary metric: Macro-average Structural Complexity Index")
    avg_ess: float = Field(..., description="Primary metric: Macro-average Energy Smell Score")
    avg_cirs: float = Field(..., description="Primary metric: Macro-average Carbon Impact Risk Score per file (gCO2eq/run)")
    total_cirs: float = Field(..., description="Secondary metric: Total summed project CIRS capacity (gCO2eq/run)")
    total_energy_joules: float = Field(..., description="Summed energy consumption in Joules across files")
    total_energy_kwh: float = Field(..., description="Summed energy consumption in kWh across files")
    total_analysis_time_sec: float = Field(..., description="Total project analysis time in seconds")
    files: list[ProjectFileResult] = Field(default_factory=list, description="Per-file detailed breakdown")


class ForecastResponse(BaseModel):
    zone: str = Field(..., description="Grid zone key")
    current_carbon_intensity: float = Field(..., description="Current carbon intensity in gCO2eq/kWh")
    lowest_forecast_intensity: float = Field(..., description="Lowest carbon intensity forecast in gCO2eq/kWh")
    percentage_reduction: float = Field(..., description="Percentage carbon reduction expected")
    recommended_execution_time: str = Field(..., description="ISO 8601 timestamp of best execution window")
    hourly_forecasts: list[dict[str, Any]] = Field(..., description="Hourly forecast data points")


