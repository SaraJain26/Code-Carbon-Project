"""Language-independent internal representation primitives.

The IR package is intentionally small in Phase 2.5. It defines stable
interfaces that future frontends and research modules can adopt gradually while
`AnalysisResult` remains the public API for Python analysis output.
"""

from analysis.ir.nodes import IRLocation, IRNode, IRNodeKind, IRScope, IRVisitor

__all__ = ["IRLocation", "IRNode", "IRNodeKind", "IRScope", "IRVisitor"]
