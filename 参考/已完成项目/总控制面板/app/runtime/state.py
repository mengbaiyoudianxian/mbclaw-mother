"""MBOS Runtime — state definitions.

ExecutionContext: per-request execution tracking.
ExecutionResult: unified return value from MotherRuntime.run().
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ExecutionStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ExecutionContext:
    """Per-request execution state. Owned by Runtime."""
    request_id: str = ""
    session_id: int = 0
    task_id: str = ""
    status: ExecutionStatus = ExecutionStatus.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def start(self):
        self.status = ExecutionStatus.RUNNING
        self.updated_at = datetime.now(timezone.utc)

    def complete(self):
        self.status = ExecutionStatus.COMPLETED
        self.updated_at = datetime.now(timezone.utc)

    def fail(self):
        self.status = ExecutionStatus.FAILED
        self.updated_at = datetime.now(timezone.utc)


@dataclass
class ExecutionResult:
    """Unified return value from MotherRuntime.run()."""
    success: bool = True
    output: str = ""
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)
