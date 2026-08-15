"""
FastAPI Backend Layer for Code-Carbon.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from carbon import get_carbon_provider
from pipeline import PredictivePipeline
from recommendation.engine import RecommendationEngine
from sustainability.metrics import ResearchSustainabilityMetrics
from api.utils import serialize_value
from api.models import HealthResponse, AnalyzeResponse

app = FastAPI(
    title="Code-Carbon API",
    description="Sustainability-First Framework for Predictive Carbon-Aware Software Engineering",
    version="0.1.0"
)

# Enable CORS for frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["General"])
def get_health() -> dict[str, str]:
    """
    Check the health of the Code-Carbon API server.
    """
    return {"status": "healthy"}


@app.get("/zones", tags=["Electricity Maps"])
def get_zones() -> dict[str, Any]:
    """
    Retrieve all supported Electricity Maps zones.
    """
    try:
        client = get_carbon_provider()
        zones = client.get_all_zones()
        return serialize_value(zones)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/search-zones", tags=["Electricity Maps"])
def search_zones(q: str = Query(..., min_length=1)) -> dict[str, Any]:
    """
    Search supported Electricity Maps zones by country or code.
    """
    try:
        client = get_carbon_provider()
        matches = client.search_zones(q)
        return serialize_value(matches)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_file(
    file: UploadFile = File(...),
    zone: str = Form("DK-DK1"),
    use_global_average: bool = Form(False)
) -> dict[str, Any]:
    """
    Upload a Python source file to execute the static analysis and carbon estimation pipeline.
    """
    if not file.filename or not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="Only Python (.py) source files are supported.")

    # Create temporary directory inside workspace
    workspace_temp_dir = Path("temp_analysis")
    workspace_temp_dir.mkdir(exist_ok=True)

    temp_path = workspace_temp_dir / f"temp_{datetime.now().timestamp()}_{file.filename}"

    try:
        # Save uploaded file
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Execute existing pipeline
        pipeline = PredictivePipeline()
        result = pipeline.run(
            source_file=temp_path,
            zone=zone,
            use_global_average=use_global_average
        )

        # Extract items from pipeline result
        smell_report = result["energy_smell_report"]
        complexity_score = result["complexity_score"]
        energy_result = result["energy_result"]
        carbon_result = result["carbon_result"]

        # Run Research Sustainability Metrics (ESS and CIRS)
        ess = ResearchSustainabilityMetrics.compute_energy_smell_score(smell_report)
        cirs_research = ResearchSustainabilityMetrics.compute_carbon_impact_risk_score(
            complexity=complexity_score,
            energy_result=energy_result,
            carbon_result=carbon_result,
            ess=ess
        )

        # Run Recommendation Engine
        engine = RecommendationEngine()
        recommendation_report = engine.generate(
            smell_report=smell_report,
            complexity=complexity_score,
            energy_result=energy_result,
            carbon_result=carbon_result
        )

        # Compile response payload
        response = {
            "filename": file.filename,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pipeline_raw": serialize_value(result),
            "research_metrics": {
                "energy_smell_score": ess,
                "carbon_impact_risk_score": cirs_research,
                "ess_version": "1.0.0-prototype",
                "cirs_version": "1.0.0-prototype",
            },
            "recommendations": serialize_value(recommendation_report),
        }

        return response

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    finally:
        # Cleanup temp file
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
