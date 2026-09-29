import unittest
import ast
from pathlib import Path

from analysis import StaticAnalysisEngine
from detector import (
    DetectionContext,
    DetectorConfiguration,
)
from detector.rules import AsyncOperationDetector, MemoryAllocationDetector
from knowledge import RuleLoader, RuleRepository


FIXTURES = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "benchmarks"
)


class AsyncDetectorTest(unittest.TestCase):

    def test_async_blocking_detection_positive(self):
        code = """
import time

async def process_items(items: list[int]):
    for item in items:
        time.sleep(0.5)
"""
        engine = StaticAnalysisEngine()
        result = engine.analyze_source(code, "test_async_pos.py")
        detector = AsyncOperationDetector()
        context = DetectionContext(
            analysis_result=result,
            rule_repository=RuleRepository(RuleLoader().load_default_rules()),
            configuration=DetectorConfiguration(),
        )
        findings = detector.detect(context)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "EKB-ASYNC-001")
        self.assertIn("time.sleep", findings[0].message)

    def test_async_legitimate_code_negative(self):
        code = """
import asyncio

async def process_items(items: list[int]):
    for item in items:
        await asyncio.sleep(0.5)
"""
        engine = StaticAnalysisEngine()
        result = engine.analyze_source(code, "test_async_neg.py")
        detector = AsyncOperationDetector()
        context = DetectionContext(
            analysis_result=result,
            rule_repository=RuleRepository(RuleLoader().load_default_rules()),
            configuration=DetectorConfiguration(),
        )
        findings = detector.detect(context)
        self.assertEqual(len(findings), 0)


class MemoryDetectorTest(unittest.TestCase):

    def test_memory_allocation_binop_positive(self):
        code = """
def process(count: int):
    for i in range(count):
        buf = [0] * 50000
"""
        engine = StaticAnalysisEngine()
        result = engine.analyze_source(code, "test_mem_pos.py")
        detector = MemoryAllocationDetector()
        context = DetectionContext(
            analysis_result=result,
            rule_repository=RuleRepository(RuleLoader().load_default_rules()),
            configuration=DetectorConfiguration(),
        )
        findings = detector.detect(context)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "EKB-MEM-001")

    def test_arithmetic_binop_negative(self):
        code = """
def calculate(count: int):
    val = 0
    for i in range(count):
        val = i * 50000
"""
        engine = StaticAnalysisEngine()
        result = engine.analyze_source(code, "test_mem_arith.py")
        detector = MemoryAllocationDetector()
        context = DetectionContext(
            analysis_result=result,
            rule_repository=RuleRepository(RuleLoader().load_default_rules()),
            configuration=DetectorConfiguration(),
        )
        findings = detector.detect(context)
        self.assertEqual(len(findings), 0)


if __name__ == "__main__":
    unittest.main()