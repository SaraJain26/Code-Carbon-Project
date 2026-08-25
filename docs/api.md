# Static Analysis Engine API

## Entry Point

```python
from analysis import StaticAnalysisEngine

engine = StaticAnalysisEngine()
result = engine.analyze_file("examples/benchmarks/nested_loops.py")
```

Use `analyze_source(source, source_file="<memory>")` for in-memory analysis.

## Result Model

`AnalysisResult` contains:

- `module`: module-level file metadata.
- `functions`: `FunctionInfo` entries with parameters, decorators, recursion, return annotations, docstrings, locals, statement count, and line count.
- `classes`: `ClassInfo` entries with inheritance, methods, decorators, class variables, and docstrings.
- `loops`: `LoopInfo` entries with loop type, line range, nesting depth, parent class/function, and structural flags.
- `calls`: `CallInfo` entries with caller, callee, line number, and call type.
- `imports`: `ImportInfo` entries classified as standard-library, third-party, or local.
- `file_operations`: detected file-system operations.
- `network_operations`: detected API/network operations.
- `async_operations`: async function, await, async for, and async with usage.
- `exceptions`: try, except, finally, raise, and custom exception usage.
- `call_graph`: directed graph with recursion helpers.
- `control_flow_graph`: lightweight CFG over functions and control constructs.
- `symbol_table`: scope-aware definitions, assignments, and references.
- `metadata`: per-AST-node location, scope, parent, depth, and node type.

## Extension Points

Each visitor has a single responsibility and can be replaced or extended without changing the parser interface:

- `FunctionVisitor`
- `ClassVisitor`
- `LoopVisitor`
- `CallVisitor`
- `ImportVisitor`
- `AsyncVisitor`
- `ExceptionVisitor`
- `SymbolVisitor`
- `MetadataVisitor`
- `CFGVisitor`

---

## FastAPI Backend Endpoints

The FastAPI backend exposes the static analysis pipeline and carbon estimation models:

### 1. `POST /analyze`
Upload a Python file to run the entire analysis pipeline, compute research sustainability metrics, and return prioritized optimization recommendations.
*   **Request Body**: Multipart form data with parameters:
    *   `file`: Python (.py) source file upload.
    *   `zone`: (Optional, default `DK-DK1`) Electricity Maps zone identifier.
    *   `use_global_average`: (Optional, default `false`) Set true to force global IEA intensity average on network failures.
*   **Response Model**: `AnalyzeResponse` containing:
    *   `filename`: string
    *   `timestamp`: ISO 8601 string
    *   `pipeline_raw`: Full raw result dictionary from the backend pipeline.
    *   `research_metrics`: `ResearchMetricsSchema` containing the Version 1 Research Prototype scores:
        *   `energy_smell_score`: Expected active leak index (ESS).
        *   `carbon_impact_risk_score`: Proportional risk exposure score (CIRS_Research) in effective gCO2eq.
    *   `recommendations`: `RecommendationReport` containing a prioritized array of optimization recommendations.

### 2. `GET /zones`
Retrieve all supported regional Electricity Maps grids and their current marginal carbon intensities.
*   **Response**: Dictionary of supported `ZoneData` structures.

### 3. `GET /search-zones`
Search supported regional grids by keyword or country code.
*   **Query Parameters**: `q` (string, minimum length 1).
*   **Response**: Filtered subset of matching `ZoneData` structures.

### 4. `GET /health`
Verify that the Code-Carbon API server is online and running healthy.
*   **Response**: `{"status": "healthy"}`

---

## Recommendation Engine API

### Entry Point
```python
from recommendation.engine import RecommendationEngine

engine = RecommendationEngine()
# Generate prioritized recommendations using pipeline reports, complexity results, and carbon values
report = engine.generate(
    smell_report=result["energy_smell_report"],
    complexity=result["complexity_score"],
    energy_result=result["energy_result"],
    carbon_result=result["carbon_result"]
)
```

---

## Sustainability Metrics API (ESS & CIRS)

### Entry Point
```python
from sustainability.metrics import ResearchSustainabilityMetrics

# 1. Compute Fuzzy Energy Smell Score (ESS)
ess = ResearchSustainabilityMetrics.compute_energy_smell_score(
    result["energy_smell_report"]
)

# 2. Compute Proportional Carbon Impact Risk Score (CIRS_Research)
cirs_research = ResearchSustainabilityMetrics.compute_carbon_impact_risk_score(
    complexity=result["complexity_score"],
    energy_result=result["energy_result"],
    carbon_result=result["carbon_result"],
    ess=ess
)
```

---

## Grid Carbon Provider Abstraction API

The framework decouples external grid API endpoints via the `CarbonIntensityProvider` abstraction. Swapping between local mock evaluation and live Electricity Maps updates is managed automatically at runtime.

### 1. Provider Interface
```python
from carbon import CarbonIntensityProvider

# Decoupled interface methods
provider.get_zone(zone: str) -> ZoneData
provider.get_all_zones() -> dict[str, ZoneData]
provider.get_latest(zone: str) -> CarbonIntensityData
provider.get_forecast(zone: str) -> list[CarbonIntensityData]
provider.search_zones(query: str) -> dict[str, ZoneData]
```

### 2. Factory Pattern Retrieval
```python
from carbon import get_carbon_provider

# Automatically retrieves ElectricityMapsProvider if ELECTRICITYMAPS_API_KEY is available,
# otherwise falls back to MockCarbonIntensityProvider
provider = get_carbon_provider()
```


