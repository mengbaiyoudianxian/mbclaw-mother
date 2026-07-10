"""MBOS Runtime — internal Event objects.

5 event types. Notification only — not a control flow mechanism.
Keep minimal. Add more only when a concrete listener requires it.
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
    """Emitted when MotherRuntime.run() receives a request."""
    event_type: str = "request"


@dataclass
class ExecutionStartEvent(Event):
    """Emitted when the agent loop begins execution."""
    event_type: str = "execution.start"


@dataclass
class ExecutionFinishEvent(Event):
    """Emitted when execution completes successfully.

    Carries the ExecutionResult — no separate ResultEvent needed.
    """
    event_type: str = "execution.finish"
    result: Optional[ExecutionResult] = None


@dataclass
class ExecutionFailedEvent(Event):
    """Emitted when execution terminates with an error."""
    event_type: str = "execution.failed"
    error: str = ""


@dataclass
class StateChangedEvent(Event):
    """Emitted when ExecutionContext status changes.

    Payload keys: old_status, new_status.
    """
    event_type: str = "state.changed"
