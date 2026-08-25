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


class AnalyzeResponse(BaseModel):
    filename: str = Field(..., description="Name of the analyzed file")
    timestamp: str = Field(..., description="ISO 8601 timestamp of when the analysis occurred")
    pipeline_raw: dict[str, Any] = Field(..., description="Raw pipeline execution results")
    research_metrics: ResearchMetricsSchema = Field(..., description="Experimental Version 1 research metrics")
    recommendations: dict[str, Any] = Field(..., description="Prioritized optimization recommendations")
