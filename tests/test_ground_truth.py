import json
import subprocess
import sys
from pathlib import Path

from detector import (DefaultCandidateExtractor, DefaultConfidenceScorer,
                      DefaultFindingGenerator, DefaultRuleEvaluator,
                      DetectionContext, DetectorConfiguration,
                      EnergySmellDetector)
from analysis import StaticAnalysisEngine
from knowledge import RuleLoader, RuleRepository
from recommendation.transformer import ASTCodeTransformer
from energy.loop_ops import loop_weighted_ops


ROOT = Path(__file__).parent / "ground_truth"


def _findings(source: str):
    analysis = StaticAnalysisEngine().analyze_source(source)
    repo = RuleRepository(RuleLoader().load_default_rules())
    detector = EnergySmellDetector(DefaultCandidateExtractor(), DefaultRuleEvaluator(),
                                   DefaultConfidenceScorer(), DefaultFindingGenerator())
    return detector.detect(DetectionContext(analysis, repo, DetectorConfiguration())).findings


def test_handwritten_ground_truth_table(capsys):
    expected = json.loads((ROOT / "expected.json").read_text())
    actual_rows = []
    for filename, expected_row in expected.items():
        source = (ROOT / filename).read_text()
        findings = _findings(source)
        transformed = ASTCodeTransformer().transform(source, findings=[
            {"rule_id": f.rule_id, "line_number": f.line_number, "category": str(f.category),
             "message": f.message} for f in findings
        ])
        changed = bool(transformed.auto_applied_fixes)
        before_ops = loop_weighted_ops(source)
        after_ops = loop_weighted_ops(transformed.optimized_code)
        direction = "lower" if after_ops < before_ops else "higher" if after_ops > before_ops else "same"
        actual = {"smell_count": len(findings), "changes": changed, "energy_direction": direction}
        compile(transformed.optimized_code, filename, "exec")
        if filename == "one_loop_invariant_call.py":
            original_run = subprocess.run([sys.executable, str(ROOT / filename)], capture_output=True, text=True, check=True)
            optimized_path = ROOT / "_temporary_optimized_ground_truth.py"
            try:
                optimized_path.write_text(transformed.optimized_code)
                optimized_run = subprocess.run([sys.executable, str(optimized_path)], capture_output=True, text=True, check=True)
            finally:
                optimized_path.unlink(missing_ok=True)
            assert optimized_run.stdout == original_run.stdout
        actual_rows.append((filename, expected_row, actual))
    print("file | expected | actual")
    for filename, expected_row, actual in actual_rows:
        print(f"{filename} | {expected_row} | {actual}")
        assert actual == expected_row, filename
