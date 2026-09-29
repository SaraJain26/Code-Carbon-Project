from __future__ import annotations

from pathlib import Path

from radon.complexity import cc_visit


class RadonAdapter:
    """
    Adapter around the Radon library.

    Computes Cyclomatic Complexity for Python source files while
    hiding Radon's API from the rest of the project.
    """

    def compute(self, source_file: str | Path) -> float:
        source_str = str(source_file)
        if not source_str.startswith("<") and Path(source_str).exists():
            try:
                source = Path(source_str).read_text(encoding="utf-8")
            except Exception:
                source = source_str
        else:
            source = source_str

        try:
            blocks = cc_visit(source)
            return float(sum(block.complexity for block in blocks))
        except Exception:
            return 0.0

    def compute_sloc(self, source_file: str | Path) -> int:
        """
        Compute non-comment, non-blank Source Lines of Code (SLOC).
        """
        if isinstance(source_file, Path):
            source = source_file.read_text(encoding="utf-8")
        else:
            source_str = str(source_file)
            if not source_str.startswith("<") and Path(source_str).exists():
                try:
                    source = Path(source_str).read_text(encoding="utf-8")
                except Exception:
                    source = source_str
            else:
                source = source_str

        try:
            from radon.raw import analyze
            raw_stats = analyze(source)
            return max(raw_stats.sloc, 1)
        except Exception:
            lines = [line.strip() for line in source.splitlines()]
            sloc_lines = [line for line in lines if line and not line.startswith("#")]
            return max(len(sloc_lines), 1)