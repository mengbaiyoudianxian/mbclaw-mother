"""MotherRuntime — DEPRECATED compat layer.

This module is replaced by app.runtime.kernel.MotherRuntime.
All imports now forward to the canonical location.

Usage:
  from app.mother_runtime import get_runtime  # still works, forwards to runtime/
  from app.runtime import get_runtime         # preferred
"""
from app.runtime.kernel import (
    MotherRuntime,
    get_runtime,
    TOOL_RE,
    THINK_RE,
)
from app.context import WorkingMemory
from app.context.engine import SYSTEM_PROMPT, TOOL_DEFS_TEXT

# Re-export for backward compat
__all__ = [
    "MotherRuntime",
    "get_runtime",
    "WorkingMemory",
    "SYSTEM_PROMPT",
    "TOOL_DEFS_TEXT",
    "TOOL_RE",
    "THINK_RE",
]
