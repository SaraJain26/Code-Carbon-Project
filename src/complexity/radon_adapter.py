from __future__ import annotations

from pathlib import Path

from radon.complexity import cc_visit


class RadonAdapter:
    """
    Adapter around the Radon library.

    Computes Cyclomatic Complexity for Python source files while
    hiding Radon's API from the rest of the project.
    """

    def compute(self, source_file: Path) -> float:
        """
        Compute the total Cyclomatic Complexity of a Python source file.

        Parameters
        ----------
        source_file:
            Path to the Python source file.

        Returns
        -------
        float
            Sum of the Cyclomatic Complexity values for all analyzed
            functions, methods, and classes.
        """

        source = source_file.read_text(encoding="utf-8")

        blocks = cc_visit(source)

        return float(sum(block.complexity for block in blocks))