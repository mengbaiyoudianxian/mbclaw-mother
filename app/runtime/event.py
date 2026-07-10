"""MBOS Runtime — Event types for the pub/sub event system.

Defines typed events used by EventBus for inter-module communication.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


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
    """Emitted when a user request enters the pipeline."""
    event_type: str = "request"


@dataclass
class ExecutionStartEvent(Event):
    """Emitted when the agent loop begins execution."""
    event_type: str = "execution.start"


@dataclass
class ExecutionFinishEvent(Event):
    """Emitted when execution completes successfully."""
    event_type: str = "execution.finish"
    result: Optional[Any] = None


@dataclass
class ExecutionFailedEvent(Event):
    """Emitted when execution terminates with an error."""
    event_type: str = "execution.failed"
    error: str = ""


@dataclass
class GovernorDenyEvent(Event):
    """Emitted when Governor denies a request."""
    event_type: str = "governor.deny"
    rule_hit: str = ""
    risk_level: str = ""


@dataclass
class PlannerCompleteEvent(Event):
    """Emitted when Planner finishes goal decomposition."""
    event_type: str = "planner.complete"
    task_count: int = 0
    goal: str = ""


@dataclass
class SchedulerDispatchEvent(Event):
    """Emitted when Scheduler selects worker+model for a task."""
    event_type: str = "scheduler.dispatch"
    worker_id: str = ""
    model: str = ""
    capability: str = ""


@dataclass
class TokenLowEvent(Event):
    """Emitted when token/quota is running low."""
    event_type: str = "token.low"
    provider: str = ""
    remaining: int = 0


@dataclass
class TaskCompleteEvent(Event):
    """Emitted when a single task completes."""
    event_type: str = "task.complete"
    task_status: str = ""


@dataclass
class AuditEvent(Event):
    """Emitted for audit logging of all pipeline stages."""
    event_type: str = "audit"
    stage: str = ""
    decision: str = ""
