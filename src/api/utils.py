"""
API serialization utilities.
"""

from __future__ import annotations

import dataclasses
from enum import Enum
from pathlib import Path
from datetime import datetime
from typing import Any

from analysis.callgraph import CallGraph
from analysis.cfg import ControlFlowGraph


def serialize_value(obj: Any) -> Any:
    """
    Recursively serialize dataclasses, enums, paths, and complex structures
    to standard JSON types.
    """
    if obj is None:
        return None
    elif isinstance(obj, (int, float, str, bool)):
        return obj
    elif isinstance(obj, dict):
        return {str(k): serialize_value(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [serialize_value(x) for x in obj]
    elif isinstance(obj, (set, frozenset)):
        return sorted([serialize_value(x) for x in obj])
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, Path):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, CallGraph):
        return {
            "nodes": sorted(list(obj.nodes)),
            "edges": [
                {
                    "caller": edge.caller,
                    "callee": edge.callee,
                    "line_number": edge.line_number,
                    "is_recursive": edge.is_recursive,
                }
                for edge in obj.edges
            ]
        }
    elif isinstance(obj, ControlFlowGraph):
        return {
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "node_type": n.node_type,
                    "line_number": n.line_number,
                    "scope": n.scope,
                }
                for n in obj.nodes
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "label": e.label,
                }
                for e in obj.edges
            ]
        }
    elif hasattr(obj, "__dataclass_fields__"):
        d = {}
        for f in dataclasses.fields(obj):
            d[f.name] = serialize_value(getattr(obj, f.name))
        return d
    elif hasattr(obj, "to_dict"):
        return serialize_value(obj.to_dict())
    else:
        # Fallback for symbol table and metadata registry to avoid cycles
        class_name = obj.__class__.__name__
        if "SymbolTable" in class_name or "MetadataRegistry" in class_name:
            return None
        return str(obj)
