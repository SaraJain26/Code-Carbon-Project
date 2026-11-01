# Code-Carbon: Demo Script & Evaluation FAQ

This document outlines the standard 5-step walkthrough for evaluating Code-Carbon, along with concise answers to core methodological questions from the research paper.

---

## 5-Step Demo Script

### Step 1: Start and Launch the Dashboard
1. Start the unified backend and frontend server:
   ```bash
   python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
   ```
2. Open your web browser to `http://127.0.0.1:8000`.
3. Confirm that the **Code-Carbon** dashboard loads, showing the navigation tabs (*Single-File Analysis*, *Project / ZIP Analysis*, *Green Scheduling*), the grid region selector, and the *Global Average Fallback* toggle (enabled by default).

### Step 2: Single-File Analysis & Energy Smell Detection
1. In the **Single-File Analysis** tab, click one of the built-in sample presets (or paste a Python script containing a loop-invariant computation).
2. Select a target grid zone (e.g., `DK-DK1` or `US-CAL-CISO`).
3. Click **Run Sustainability Audit**.
4. Inspect the top metric cards displaying **Estimated Energy (Joules)**, **Research CIRS (risk index)**, **Energy Smell Score (ESS / 10)**, and the detected code findings categorized by severity.

### Step 3: AST Refactoring & Invariance Verification
1. Scroll down to the **Automated AST Refactoring & Impact** section.
2. Observe the generated refactored code:
   - If auto-fixes apply (e.g., `EKB-COMP-002` loop-invariant hoisting), the code is safely restructured.
   - If no auto-fixes apply, the original source code is preserved without destructive comment stripping.
3. Review the **Refactor Comparison**:
   - **SCI (Before → After)**: Remains invariant or decreases (does not artificially inflate due to removed comments/collapsed formatting).
   - **Energy Smells (Before → After)**: Shows actionable smells resolved and burden reduction.
   - **Measured Speedup**: Displays empirical runtime measurements if `ENABLE_SANDBOX_EXEC=true`, or `disabled` if running in restricted environments.

### Step 4: Multi-File Project & ZIP Archive Analysis
1. Switch to the **Project / ZIP Analysis** tab.
2. Drag and drop a `.zip` archive or multiple `.py` files.
3. View the aggregated project metrics:
   - **Macro-Avg SCI**, **Macro-Avg ESS**, and **Primary Research CIRS (risk index)**.
   - **Total Project Energy (Joules & kWh)** and **Project Carbon Footprint (gCO₂eq)**.
4. Inspect the **Top Energy Smells Hotspot** and the file-by-file distribution table to prioritize optimization targets.

### Step 5: Regional Grid Carbon Intensity & Green Scheduling
1. Switch to the **Green Scheduling** tab.
2. Pick any supported Electricity Maps grid zone. If running offline or without an API key, the system automatically falls back to curated mock grid intensities without failing.
3. Review the 24-hour carbon forecast chart and note the **Optimal Execution Window** offering maximum operational carbon reduction.

---

## Frequently Asked Questions

### 1. Why is ESS 10 or 0 for most files?
**Answer:** The Energy Smell Score (ESS) is a prototype heuristic metric that saturates quickly. Because each detected high-confidence energy smell adds a significant penalty weight relative to code length, even a small number of smells can drive the score directly to the maximum ceiling of 10.0, while clean files remain at 0.0.

### 2. Is energy measured?
**Answer:** No. The energy values reported in the primary static analysis pipeline are static model estimates based on structural code complexity metrics (Cyclomatic Complexity, Nesting Depth, and Function Density) evaluated against a calibrated 55 W reference power baseline. They are not direct hardware wattmeter measurements.

### 3. Why does energy not change after refactoring?
**Answer:** The static energy model depends strictly on structural complexity (control flow branch count, nesting depth, and lines of code). When automated AST refactorings resolve semantic efficiency smells (such as hoisting an invariant computation or re-using a buffer) without altering the macro control-flow graph, the structural complexity metrics remain essentially identical. Furthermore, the paper's calibration demonstrates that static code metrics explain very little runtime energy variance.

### 4. Is CIRS a real carbon measurement?
**Answer:** No. Carbon Impact Risk Score (CIRS) is a relative risk indicator, not a physical carbon emission measurement. It combines static energy hazard (modelled energy $\times$ regional grid carbon intensity) with structural and smell exposure ($SCI \times (1 + ESS/10)$) to rank code components by operational carbon risk.
