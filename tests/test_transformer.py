"""
Unit tests for ASTCodeTransformer.
Verifies AST transformation producing valid, syntactically correct, runnable Python
for the 4 auto-applicable rule types: EKB-COMP-002, EKB-IO-001, EKB-IO-002, EKB-MEM-001.
"""

import ast
from recommendation.transformer import ASTCodeTransformer


def test_transformer_ekb_comp_002_redundant_computation():
    code = """
def compute_data():
    results = []
    for i in range(10):
        factor = 3.14159 * 42.0
        results.append(i * factor)
    return results
"""
    transformer = ASTCodeTransformer()
    res = transformer.transform(code)
    
    # 1. Assert syntactically valid Python
    tree = ast.parse(res.optimized_code)
    assert tree is not None
    
    # 2. Assert runnable Python with same output
    loc_orig = {}
    exec(code, globals(), loc_orig)
    orig_output = loc_orig["compute_data"]()

    loc_opt = {}
    exec(res.optimized_code, globals(), loc_opt)
    opt_output = loc_opt["compute_data"]()

    assert orig_output == opt_output
    assert len(res.auto_applied_fixes) >= 1
    assert any(fix["rule_id"] == "EKB-COMP-002" for fix in res.auto_applied_fixes)


def test_transformer_ekb_io_001_file_io_inside_loop(tmp_path):
    log_file = tmp_path / "test_log.txt"
    code = f"""
def write_logs():
    lines = ["a\\n", "b\\n", "c\\n"]
    for line in lines:
        with open(r"{log_file}", "a") as f:
            f.write(line)
"""
    transformer = ASTCodeTransformer()
    res = transformer.transform(code)

    # Assert syntactically valid Python
    tree = ast.parse(res.optimized_code)
    assert tree is not None

    # Assert runnable Python
    loc_opt = {}
    exec(res.optimized_code, globals(), loc_opt)
    loc_opt["write_logs"]()

    assert log_file.read_text() == "a\nb\nc\n"
    assert len(res.auto_applied_fixes) >= 1
    assert any(fix["rule_id"] in {"EKB-IO-001", "EKB-IO-002"} for fix in res.auto_applied_fixes)


def test_transformer_ekb_mem_001_temporary_allocation():
    code = """
def process_allocations():
    total = 0
    for i in range(5):
        temp_buf = [1, 2, 3, 4, 5]
        total += sum(temp_buf) + i
    return total
"""
    transformer = ASTCodeTransformer()
    res = transformer.transform(code)

    # Assert syntactically valid Python
    tree = ast.parse(res.optimized_code)
    assert tree is not None

    # Assert runnable Python
    loc_orig = {}
    exec(code, globals(), loc_orig)
    orig_val = loc_orig["process_allocations"]()

    loc_opt = {}
    exec(res.optimized_code, globals(), loc_opt)
    opt_val = loc_opt["process_allocations"]()

    assert orig_val == opt_val
    assert len(res.auto_applied_fixes) >= 1
    assert any(fix["rule_id"] == "EKB-MEM-001" for fix in res.auto_applied_fixes)


def test_transformer_bucket_values_correctness():
    code = """
def bucket_values(values):
    output = []
    for v in values:
        bucket = []
        bucket.append(v * 2)
        output.append(bucket[0])
    return output
"""
    transformer = ASTCodeTransformer()
    res = transformer.transform(code)

    loc_orig = {}
    exec(code, globals(), loc_orig)
    orig_output = loc_orig["bucket_values"]([1, 2, 3])

    loc_opt = {}
    exec(res.optimized_code, globals(), loc_opt)
    opt_output = loc_opt["bucket_values"]([1, 2, 3])

    assert orig_output == [2, 4, 6]
    assert opt_output == [2, 4, 6]


def test_transformer_comment_stripping_sci_invariance(tmp_path):
    """
    Regression test: ensures AST refactoring (which strips comments) does NOT
    artificially inflate Function Density (FD) or Structural Complexity Index (SCI),
    and ensures predicted reduction percent is non-negative when smells are fixed.
    """
    from pipeline import PredictivePipeline
    from sustainability.metrics import ResearchSustainabilityMetrics

    code = """
# Header Comment 1
# Header Comment 2
# Header Comment 3

def process_file_io(items):
    # Smell 1: Repeated file open in loop
    for item in items:
        with open("log.txt", "a") as f:
            f.write(str(item))

# Middle Comment 1
# Middle Comment 2

def process_invariant(numbers):
    # Smell 2: Loop invariant computation
    res = []
    for num in numbers:
        multiplier = 42 * 100
        res.append(num * multiplier)
    return res

# Footer Comment 1
# Footer Comment 2
"""
    file_before = tmp_path / "test_comments.py"
    file_before.write_text(code, encoding="utf-8")

    pipeline = PredictivePipeline()
    result_before = pipeline.run(file_before, zone="DK-DK1")

    transformer = ASTCodeTransformer()
    transform_res = transformer.transform(code)

    file_after = tmp_path / "test_comments_opt.py"
    file_after.write_text(transform_res.optimized_code, encoding="utf-8")

    result_after = pipeline.run(file_after, zone="DK-DK1")

    sci_before = result_before["complexity_score"].structural_complexity_index
    sci_after = result_after["complexity_score"].structural_complexity_index

    fd_before = result_before["complexity_metrics"].function_density
    fd_after = result_after["complexity_metrics"].function_density

    # 1. Function Density and SCI should not increase due to comment removal
    assert fd_after <= fd_before + 1e-4
    assert sci_after <= sci_before + 1e-4

    # 2. Predicted reduction percent calculation
    ess_before = ResearchSustainabilityMetrics.compute_energy_smell_score(result_before["energy_smell_report"])
    ess_after = ResearchSustainabilityMetrics.compute_energy_smell_score(result_after["energy_smell_report"])
    
    intensity = result_before["carbon_result"].carbon_data.carbon_intensity
    energy_kwh_before = result_before["energy_result"].energy.energy_joules / 3_600_000.0
    energy_kwh_after = result_after["energy_result"].energy.energy_joules / 3_600_000.0

    hazard_before = energy_kwh_before * intensity
    hazard_after = energy_kwh_after * intensity

    exposure_before = sci_before * (1.0 + (ess_before / 10.0))
    exposure_after = sci_after * (1.0 + (ess_after / 10.0))

    cirs_before = hazard_before * exposure_before
    cirs_after = hazard_after * exposure_after

    predicted_reduction = ((cirs_before - cirs_after) / cirs_before) * 100.0 if cirs_before > 0 else 0.0

    # Must not be negative!
    assert predicted_reduction >= 0.0


