"""MBOS Runtime — internal Event objects v2.

v2: Added tool_call, tool_result, system_alert, token_low, worker_failed, memory_update.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .state import ExecutionResult


@dataclass
class Event:
    """Base event. All runtime events inherit from this."""
    event_id: str
    event_type: str
    request_id: str = ""
    session_id: int = 0
    task_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


@dataclass
class RequestEvent(Event):
    event_type: str = "user_message"


@dataclass
class ExecutionStartEvent(Event):
    event_type: str = "execution.start"


@dataclass
class ExecutionFinishEvent(Event):
    event_type: str = "execution.finish"
    result: Optional[ExecutionResult] = None


@dataclass
class ExecutionFailedEvent(Event):
    event_type: str = "execution.failed"
    error: str = ""


@dataclass
class StateChangedEvent(Event):
    event_type: str = "state.changed"


@dataclass
class ToolCallEvent(Event):
    """Emitted before a tool is executed."""
    event_type: str = "tool_call"
    tool_name: str = ""
    arguments: str = ""


@dataclass
class ToolResultEvent(Event):
    """Emitted after a tool completes."""
    event_type: str = "tool_result"
    tool_name: str = ""
    status: str = ""
    elapsed_ms: float = 0.0
    error: str = ""


@dataclass
class SystemAlertEvent(Event):
    event_type: str = "system_alert"
    severity: str = "info"  # info | warning | critical


@dataclass
class TokenLowEvent(Event):
    event_type: str = "token_low"
    provider: str = ""
    remaining: int = 0


@dataclass
class WorkerFailedEvent(Event):
    event_type: str = "worker_failed"
    worker_id: str = ""
    error: str = ""


@dataclass
class MemoryUpdateEvent(Event):
    event_type: str = "memory_update"
    key: str = ""
    operation: str = "store"  # store | delete | update


# ── Event type registry ─────────────────────────────────────
ALL_EVENT_TYPES = [
    "user_message", "execution.start", "execution.finish", "execution.failed",
    "state.changed", "tool_call", "tool_result",
    "system_alert", "token_low", "worker_failed", "memory_update",
]