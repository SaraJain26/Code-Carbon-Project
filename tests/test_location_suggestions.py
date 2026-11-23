import ast

from pipeline import PredictivePipeline
from recommendation.location_suggestions import build_location_suggestions


PIPELINE = PredictivePipeline()


def analyze(source):
    result = PIPELINE._analysis_engine.analyze_source(source)
    return [
        {
            "rule_id": finding.rule_id,
            "line_number": finding.line_number,
            "confidence": float(getattr(finding.confidence, "value", 1.0)),
        }
        for finding in PIPELINE._detect(result).findings
    ]


def _suggest(source, rule_id):
    before_findings = analyze(source)
    finding = next(item for item in before_findings if item["rule_id"] == rule_id)
    result = build_location_suggestions(source, [finding], analyzer=analyze)[0]
    return result, before_findings


def _assert_equivalent(source, suggestion, result_name):
    replacement = suggestion["replacement_code"]
    assert replacement
    assert ast.dump(ast.parse(source), include_attributes=False) != ast.dump(ast.parse(source.replace(suggestion["original_code"], replacement, 1)), include_attributes=False)
    rewritten = source.replace(suggestion["original_code"], replacement, 1)
    ast.parse(rewritten)
    before, after = {}, {}
    exec(source, before, before)
    exec(rewritten, after, after)
    assert before[result_name] == after[result_name]
    after_findings = analyze(rewritten)
    assert len(after_findings) < len(analyze(source))
    assert all(sum(item["rule_id"] == rule for item in after_findings) <= sum(item["rule_id"] == rule for item in analyze(source)) for rule in {item["rule_id"] for item in after_findings})


def test_loop_invariant_assignment_with_zero_iteration_binding_is_review_only():
    source = """items = [2, 5, 9]
output = []
for item in items:
    factor = 3 * 7
    output.append((item, factor))
"""
    suggestion, _ = _suggest(source, "EKB-COMP-002")
    assert suggestion["status"] == "no_safe_rewrite"
    assert suggestion["replacement_code"] is None
    assert "zero times" in suggestion["reason"]


def test_nested_registered_collections_without_isolated_test_runner_are_review_only():
    source = """rows = [[1, 2], [], [3, 4]]
results = []
for row in rows:
    for value in row:
        results.append(value)
"""
    suggestion, _ = _suggest(source, "EKB-COMP-001")
    assert suggestion["status"] == "no_safe_rewrite"
    assert suggestion["replacement_code"] is None
    assert suggestion["reason"]


def test_nested_lookup_without_isolated_test_runner_is_review_only():
    source = """keys = ["a", "b", "a"]
rows = ["b", "a", "a"]
matches = []
for key in keys:
    for row in rows:
        if row == key:
            matches.append(row)
"""
    suggestion, _ = _suggest(source, "EKB-COMP-001")
    assert suggestion["status"] == "no_safe_rewrite"
    assert suggestion["replacement_code"] is None
    assert suggestion["reason"]


def test_recursion_finding_without_verified_candidate_is_review_only():
    source = "class Handler:\n    def __init__(self):\n        setup()\n"
    result = build_location_suggestions(source, [{"rule_id": "EKB-COMP-003", "line_number": 2}], analyzer=analyze)[0]
    assert result["status"] == "no_safe_rewrite"
    assert result["replacement_code"] is None
    assert result["reason"]


def test_file_io_inside_loop_without_isolated_test_runner_is_review_only():
    source = """rows = ['a', 'b']
log = []
for row in rows:
    with open('test_dummy.txt', 'w') as f:
        log.append(row)
"""
    suggestion, before_findings = _suggest(source, "EKB-IO-001")
    assert suggestion["status"] == "no_safe_rewrite"
    assert suggestion["replacement_code"] is None
    assert suggestion["reason"]


def test_no_safe_rewrite_never_exposes_placeholder_code():
    source = "for item in items:\n    client.test_client().get(item)\n"
    result = build_location_suggestions(source, [{"rule_id": "EKB-NET-001", "line_number": 2}], analyzer=analyze)[0]
    assert result["status"] == "no_safe_rewrite"
    assert result["replacement_code"] is None
    assert result["reason"]


def test_no_shown_replacement_equals_original():
    sources_and_rules = [
        ("""items = [1, 2]
output = []
for item in items:
    factor = 10
    output.append((item, factor))
""", "EKB-COMP-002"),
        ("""rows = [[1], [2]]
results = []
for row in rows:
    for val in row:
        results.append(val)
""", "EKB-COMP-001"),
        ("""keys = ['a']
rows = ['a']
matches = []
for k in keys:
    for r in rows:
        if r == k:
            matches.append(r)
""", "EKB-COMP-001"),
        ("""rows = ['x']
log = []
for r in rows:
    with open('dummy.txt', 'w') as f:
        log.append(r)
""", "EKB-IO-001"),
    ]
    for source, rule_id in sources_and_rules:
        suggestion, _ = _suggest(source, rule_id)
        if suggestion.get("replacement_code"):
            orig = suggestion["original_code"]
            repl = suggestion["replacement_code"]
            assert repl != orig
            assert repl.strip() != orig.strip()
            assert ast.dump(ast.parse(repl), include_attributes=False) != ast.dump(ast.parse(orig), include_attributes=False)


def test_empty_syntax_error_python2_and_oversized_inputs_return_clean_states():
    finding = {"rule_id": "EKB-COMP-002", "line_number": 1}
    for source in ("", "def broken(:\n", "print 'python 2'\n"):
        suggestion = build_location_suggestions(source, [finding])[0]
        assert suggestion["replacement_code"] is None
        assert suggestion["reason"]
    large = "# data\n" * 400_000
    suggestion = build_location_suggestions(large, [finding])[0]
    assert suggestion["replacement_code"] is None
    assert "2 MB" in suggestion["reason"]

