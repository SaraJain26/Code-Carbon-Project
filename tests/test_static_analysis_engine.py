import unittest
from pathlib import Path

from analysis import StaticAnalysisEngine
from analysis.models import CallType, ImportType, LoopType


FIXTURES = Path(__file__).resolve().parents[1] / "examples" / "benchmarks"


class StaticAnalysisEngineTest(unittest.TestCase):
    def test_function_class_and_loop_analysis(self) -> None:
        result = StaticAnalysisEngine().analyze_file(FIXTURES / "nested_loops.py")

        functions = {function.name: function for function in result.functions}
        self.assertIn("bubble_sort", functions)
        self.assertEqual(functions["bubble_sort"].parameters[0].name, "values")
        self.assertEqual(functions["bubble_sort"].return_annotation, "list[int]")

        loops = result.loops
        self.assertGreaterEqual([loop.loop_type for loop in loops].count(LoopType.FOR), 3)
        self.assertEqual(max(loop.nesting_depth for loop in loops), 2)
        self.assertTrue(any(loop.parent_function == "bubble_sort" for loop in loops))

    def test_recursion_and_call_graph(self) -> None:
        result = StaticAnalysisEngine().analyze_file(FIXTURES / "recursive_algorithms.py")

        functions = {function.name: function for function in result.functions}
        self.assertTrue(functions["fibonacci"].is_recursive)
        self.assertIn("fibonacci", result.call_graph.recursive_functions())
        self.assertIn(("is_even", "is_odd"), result.call_graph.mutual_recursions())

    def test_async_network_and_call_classification(self) -> None:
        result = StaticAnalysisEngine().analyze_file(FIXTURES / "async_network.py")

        self.assertTrue(any(function.name == "fetch_all" and function.is_async for function in result.functions))
        self.assertTrue(any(operation.operation == "await" for operation in result.async_operations))
        self.assertTrue(any(operation.library == "requests" for operation in result.network_operations))
        self.assertTrue(any(call.callee == "requests.get" and call.call_type == CallType.LIBRARY for call in result.calls))

    def test_file_import_and_symbol_analysis(self) -> None:
        result = StaticAnalysisEngine().analyze_file(FIXTURES / "file_processing.py")

        self.assertTrue(any(operation.operation == "open" for operation in result.file_operations))
        self.assertTrue(any(operation.operation == "writer.write" for operation in result.file_operations))
        self.assertTrue(any(import_info.module == "os" and import_info.import_type == ImportType.STANDARD_LIBRARY for import_info in result.imports))
        self.assertIn("copy_lines", result.symbol_table.scopes)
        self.assertIn("count", result.symbol_table.scopes["copy_lines"].symbols)

    def test_classes_exceptions_cfg_and_metadata(self) -> None:
        result = StaticAnalysisEngine().analyze_file(FIXTURES / "classes_exceptions.py")

        classes = {class_info.name: class_info for class_info in result.classes}
        self.assertEqual(classes["StreamingProcessor"].bases, ["Processor"])
        self.assertIn("batch_size", classes["Processor"].class_variables)
        self.assertTrue(any(exception.operation == "custom_exception" for exception in result.exceptions))
        self.assertTrue(any(exception.operation == "raise" for exception in result.exceptions))
        self.assertGreater(len(result.control_flow_graph.nodes), 0)
        self.assertGreater(len(result.metadata), 0)


if __name__ == "__main__":
    unittest.main()
