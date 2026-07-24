from __future__ import annotations

from analysis.models import AnalysisResult

from complexity.models import ComplexityMetrics

from complexity.radon_adapter import RadonAdapter

class ComplexityMetricsExtractor:
    
    def __init__(self):
        self._radon = RadonAdapter()
    

    def extract(
        self,
        analysis_result: AnalysisResult,
        energy_smell_score: float = 0.0,
    ) -> ComplexityMetrics:

        function_count = len(analysis_result.functions)

        class_count = len(analysis_result.classes)

        loop_count = len(analysis_result.loops)

        lines_of_code = analysis_result.module.line_count

        max_nesting_depth = max(
            (loop.nesting_depth for loop in analysis_result.loops),
            default=0,
        )

        function_density = (
            function_count / lines_of_code
            if lines_of_code > 0
            else 0.0
        )

        cyclomatic_complexity = self._radon.compute(
            analysis_result.module.source_file
        )

        return ComplexityMetrics(
            cyclomatic_complexity=cyclomatic_complexity,
            max_nesting_depth=max_nesting_depth,
            function_count=function_count,
            class_count=class_count,
            loop_count=loop_count,
            lines_of_code=lines_of_code,
            function_density=function_density,
            energy_smell_score=energy_smell_score,
        )