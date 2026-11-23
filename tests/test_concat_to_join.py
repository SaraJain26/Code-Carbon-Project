import ast

import pytest

from recommendation.transformer import concat_to_join, recommend


def same_behavior(source, candidate, invoke):
    original_ns = {"__name__": "sample", "identity_decorator": identity_decorator}
    candidate_ns = {"__name__": "sample", "identity_decorator": identity_decorator}
    exec(compile(source, "<original>", "exec"), original_ns)
    exec(compile(candidate, "<candidate>", "exec"), candidate_ns)
    return invoke(original_ns) == invoke(candidate_ns)


def call(name, *args):
    return lambda ns: ns[name](*args)


def async_call(name, *args):
    def invoke(ns):
        coroutine = ns[name](*args)
        try:
            coroutine.send(None)
        except StopIteration as completed:
            return completed.value
        raise AssertionError("sample async function unexpectedly suspended")
    return invoke


def identity_decorator(fn):
    return fn


REWRITE_CASES = [
    pytest.param(
        'def build(parts):\n    s = ""\n    for part in parts:\n        s += part\n    return s\n',
        call("build", ["a", "bc", "d"]), id="basic",
    ),
    pytest.param(
        'def build(rows):\n    s = ""\n    for k, v in rows.items():\n        s += k + v\n    return s\n',
        call("build", {"a": "1", "b": "2"}), id="tuple-unpacking-items",
    ),
    pytest.param(
        'def build(parts):\n    s = "a"\n    for part in parts:\n        s += part\n    return s\n',
        call("build", ["b", "c"]), id="non-empty-init",
    ),
    pytest.param(
        'def decorate(fn):\n    return fn\n\n@decorate\n@identity_decorator\ndef build(parts):\n    s = ""\n    for part in parts:\n        s += part\n    return s\n',
        call("build", ["x", "y"]), id="stacked-decorators",
    ),
    pytest.param(
        'async def build(parts):\n    s = ""\n    for part in parts:\n        s += part\n    return s\n',
        async_call("build", ["async", "!"]), id="async-def",
    ),
    pytest.param(
        'def build(parts):\r\n\ts = ""\r\n\tfor part in parts:\r\n\t\ts += part\r\n\treturn s\r\n',
        call("build", ["tab", "bed"]), id="tabs-crlf",
    ),
    pytest.param(
        'parts = ["m", "n"]\ns = ""\nfor part in parts:\n    s += part\n',
        lambda ns: ns["s"], id="module-level",
    ),
    pytest.param(
        's = "global"\ndef build(parts):\n    global s\n    s = ""\n    for part in parts:\n        s += part\n    return s\n',
        call("build", ["g", "!", "!"]), id="global-accumulator",
    ),
]


@pytest.mark.parametrize(("source", "invoke"), REWRITE_CASES)
def test_rewrite_cases_preserve_behavior(source, invoke):
    result = recommend(source)
    assert result is not None
    assert result["transformer"] == "concat_to_join"
    ast.parse(result["new_source"])
    assert same_behavior(source, result["new_source"], invoke)
    if "\r\n" in source:
        assert result["new_source"].replace("\r\n", "").count("\n") == 0
        old_lines = source.splitlines(keepends=True)
        new_lines = result["new_source"].splitlines(keepends=True)
        assert old_lines[0] == new_lines[0]
        assert old_lines[4:] == new_lines[2:]


REFUSE_CASES = [
    pytest.param(
        'def build(parts):\n    s = ""\n    for part in parts:\n        s += part\n    return part\n',
        id="loop-var-used-after-loop",
    ),
    pytest.param(
        'def build(parts):\n    s = ""\n    for part in parts:\n        s += s[:1] + part\n    return s\n',
        id="accumulator-read-in-loop",
    ),
    pytest.param(
        'def build(parts):\n    s = 0\n    for part in parts:\n        s += part\n    return s\n',
        id="integer-init",
    ),
    pytest.param(
        'parts = ["a"]\nfor outer in range(2):\n    seen = x\n    s = ""\n    for x in parts:\n        s += x\n',
        id="outer-loop-leak-read-before-loop",
    ),
    pytest.param(
        'def build(parts):\n    s = ""\n    # meaningful comment\n    for part in parts:\n        s += part\n    return s\n',
        id="comment-between-init-and-loop",
    ),
    pytest.param(
        'def build(parts):\n    s = ""\n    while parts:\n        s += parts.pop()\n    return s\n',
        id="while-loop",
    ),
    pytest.param(
        'def build(parts):\n    s = ""\n    for part in parts:\n        s += part\n    else:\n        s += "!"\n    return s\n',
        id="for-else",
    ),
]


@pytest.mark.parametrize("source", REFUSE_CASES)
def test_unsafe_or_unsupported_cases_are_refused(source):
    assert concat_to_join(source) is None
    candidate = recommend(source)
    assert candidate is not None
    assert candidate["transformer"] == "template_comment_fallback"
    assert candidate["new_source"] != source
    ast.parse(candidate["new_source"])
    compile(candidate["new_source"], "<candidate>", "exec")
    additions = [line[1:] for line in candidate["diff"].splitlines(keepends=True)
                 if line.startswith("+") and not line.startswith("+++")]
    removals = [line for line in candidate["diff"].splitlines()
                if line.startswith("-") and not line.startswith("---")]
    assert len(additions) == 1
    assert not removals
    assert candidate["new_source"].replace(additions[0], "", 1) == source


def test_rewrite_preserves_unrelated_source_and_only_diffs_init_through_loop():
    source = '''"""This module has a\nmulti-line string."""\n\ndef build(parts):\n    # keep this comment and quote style\n    label = 'quoted value'\n    s = ""\n    for part in parts:\n        s += part\n    return label, s\n'''
    result = recommend(source)
    assert result is not None
    rewritten = result["new_source"]
    old_lines = source.splitlines(keepends=True)
    new_lines = rewritten.splitlines(keepends=True)
    start, end = 7, 9  # one-based init through loop end
    assert "".join(old_lines[:start - 1]) == "".join(new_lines[:start - 1])
    assert "".join(old_lines[end:]) == "".join(new_lines[start:])
    assert '"""This module has a\nmulti-line string."""' in rewritten
    assert "label = 'quoted value'" in rewritten
    assert "# keep this comment and quote style" in rewritten
    assert "\\n" not in rewritten
    edits = [line for line in result["diff"].splitlines() if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))]
    assert sum(line.startswith("-") for line in edits) == 3
    assert sum(line.startswith("+") for line in edits) == 1
    assert same_behavior(source, rewritten, call("build", ["first", "second"]))


TEMPLATE_SHAPES = [
    "def run(values):\n    for value in values:\n        consume(value)\n",
    "def run(values):\n    while values:\n        consume(values.pop())\n",
    "class Worker:\n    def run(self, values):\n        for value in values:\n            self.consume(value)\n",
    "async def run(values):\n    for value in values:\n        await consume(value)\n",
    "def run(mapping):\n    for key, value in mapping.items():\n        consume(key, value)\n",
    "def run(values):\n    for value in values:\n        if stop(value):\n            break\n        consume(value)\n",
    "@staticmethod\ndef run(values):\n    for value in values:\n        consume(value)\n",
    "for value in values:\n    consume(value)\n",
]
TEMPLATE_RULES = [
    "EKB-COMP-001", "EKB-COMP-002", "EKB-COMP-003", "EKB-IO-001",
    "EKB-NET-001", "EKB-ASYNC-001", "EKB-MEM-001",
]
CONCRETE_TEMPLATES = [
    ("EKB-COMP-001", "def run(keys, rows):\n    out = []\n    for key in keys:\n        for row in rows:\n            if row == key:\n                out.append(row)\n    return out\n", "set(rows)", "template_nested_lookup_set"),
    ("EKB-COMP-002", "def run(values):\n    out = []\n    for value in values:\n        factor = 10\n        out.append(value * factor)\n    return out\n", "factor = 10", "template_loop_invariant"),
    ("EKB-COMP-003", "def run(n):\n    if n < 2:\n        return n\n    return run(n - 1) + run(n - 2)\n", "lru_cache", "template_recursion_cache"),
    ("EKB-IO-001", "def run(rows):\n    for row in rows:\n        with open('out.txt', 'a') as stream:\n            stream.write(row)\n", "with open", "template_open_outside_loop"),
    ("EKB-NET-001", "def run(urls):\n    for url in urls:\n        requests.get(url)\n", "requests.Session", "template_requests_session"),
    ("EKB-ASYNC-001", "async def run(values):\n    for value in values:\n        time.sleep(value)\n", "asyncio.to_thread", "template_asyncio_to_thread"),
    ("EKB-MEM-001", "def run(values):\n    result = []\n    for value in values:\n        result.append(value * 2)\n    return result\n", "[value * 2 for value in values]", "template_list_comprehension"),
]


@pytest.mark.parametrize("rule_id,source,expected,label", CONCRETE_TEMPLATES)
def test_each_rule_uses_its_concrete_local_template(rule_id, source, expected, label):
    result = recommend(source, {"rule_id": rule_id, "line_number": 2})
    assert result is not None
    assert result["transformer"] == label
    assert expected in result["new_source"]
    assert result["new_source"] != source
    ast.parse(result["new_source"])
    compile(result["new_source"], "<concrete-template>", "exec")


def test_unmatched_template_adds_only_indented_kb_comment_and_preserves_crlf_bytes():
    from knowledge.loader import RuleLoader

    source = (
        "def run(rows):\r\n"
        "\t# keep this existing comment\r\n"
        "\tfor row in rows:\r\n"
        "\t\tif should_keep(row):\r\n"
        "\t\t\tconsume(row)\r\n"
    )
    finding = {"rule_id": "EKB-IO-001", "line_number": 4}
    result = recommend(source, finding)
    assert result is not None
    assert result["transformer"] == "template_comment_fallback"
    recommendation = next(rule.recommendation for rule in RuleLoader().load_default_rules() if rule.id == "EKB-IO-001")
    expected_comment = f"\t\t# Energy smell (EKB-IO-001): {recommendation}\r\n"
    assert expected_comment in result["new_source"]
    assert result["new_source"].replace(expected_comment, "", 1) == source
    assert "\n" not in result["new_source"].replace("\r\n", "")
    ast.parse(result["new_source"])
    compile(result["new_source"], "<comment-fallback>", "exec")


@pytest.mark.parametrize("rule_id", TEMPLATE_RULES)
@pytest.mark.parametrize("source", TEMPLATE_SHAPES)
def test_loose_templates_compile_and_change_every_supported_rule_shape(rule_id, source):
    finding = {"rule_id": rule_id, "line_number": 2}
    candidate = recommend(source, finding)
    assert candidate is not None
    assert candidate["new_source"] != source
    ast.parse(candidate["new_source"])
    compile(candidate["new_source"], "<template-test>", "exec")


def test_registry_exposes_only_the_new_recommendation_transformer():
    from recommendation.transformer import TRANSFORMER_REGISTRY

    assert TRANSFORMER_REGISTRY["EKB-MEM-001"] is concat_to_join


def test_location_cards_use_registry_candidate_and_same_rewrite_region():
    from recommendation.location_suggestions import build_location_suggestions
    from recommendation.transformer import analyze

    source = 'def build(parts):\n    s = ""\n    for part in parts:\n        s += part\n    return s\n'
    finding = {"rule_id": "EKB-MEM-001", "line_number": 4}

    def analyze_as_findings(text):
        return [
            {"rule_id": rule_id}
            for rule_id, count in analyze(text).items()
            for _ in range(count)
        ]

    card = build_location_suggestions(source, [finding], analyzer=analyze_as_findings)[0]
    assert card["transformer"] == "concat_to_join"
    assert card["original"] == card["original_code"]
    assert card["replacement"] == card["replacement_code"]
    assert card["diff"]
    assert card["line_start"] == 2
    assert card["line_end"] == 4
    assert same_behavior(source, source.replace(card["original"], card["replacement"], 1), call("build", ["a", "b"]))
