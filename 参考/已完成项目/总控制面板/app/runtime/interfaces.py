"""MBOS Runtime — interface placeholders.

These are FUTURE interfaces for modules NOT yet extracted.
They exist to define the dependency contract. DO NOT implement here.

Implementation tasks:
  - ContextEngine  → Future Task (Context Engine)
  - Governor       → Future Task (Governor)
  - Scheduler      → Future Task (Scheduler)
  - Planner        → Future Task (Planner)
  - MemoryReader   → Future Task (Memory)
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class ContextEngineProtocol(Protocol):
    """Future: build prompt context from session + message."""
    def build(self, session_id: int, message: str) -> list[dict]:
        ...


@runtime_checkable
class GovernorProtocol(Protocol):
    """Future: policy check per execution step."""
    def check(self, step: dict) -> bool:
        ...


@runtime_checkable
class SchedulerProtocol(Protocol):
    """Future: dispatch LLM/tool execution."""
    def dispatch(self, step: dict) -> dict:
        ...


@runtime_checkable
class PlannerProtocol(Protocol):
    """Future: decompose goal into steps."""
    def plan(self, goal: str) -> list[dict]:
        ...


@runtime_checkable
class MemoryReaderProtocol(Protocol):
    """Future: query memory store."""
    def query(self, text: str, top_n: int) -> list:
        ...
