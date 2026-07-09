"""MBOS Runtime Kernel v1.

MotherRuntime is the ONLY execution entry point.
All callers → MotherRuntime.run().

Exports:
  MotherRuntime  — single execution kernel
  get_runtime()  — singleton factory
  ExecutionContext, ExecutionResult, ExecutionStatus — state types
  Lifecycle      — lifecycle phases
  EventBus       — per-runtime synchronous event bus
  Event, RequestEvent, ExecutionStartEvent, ExecutionFinishEvent,
    ExecutionFailedEvent, StateChangedEvent — event types
  EventHandler   — read-only observer protocol
"""
from .kernel import MotherRuntime, get_runtime, WorkingMemory
from .state import ExecutionContext, ExecutionResult, ExecutionStatus
from .lifecycle import Lifecycle
from .event_bus import EventBus
from .event import (
    Event,
    RequestEvent,
    ExecutionStartEvent,
    ExecutionFinishEvent,
    ExecutionFailedEvent,
    StateChangedEvent,
)
from .handler import EventHandler

__all__ = [
    "MotherRuntime",
    "get_runtime",
    "WorkingMemory",
    "ExecutionContext",
    "ExecutionResult",
    "ExecutionStatus",
    "Lifecycle",
    "EventBus",
    "Event",
    "RequestEvent",
    "ExecutionStartEvent",
    "ExecutionFinishEvent",
    "ExecutionFailedEvent",
    "StateChangedEvent",
    "EventHandler",
]
