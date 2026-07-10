"""MBOS Worker — typed worker with capability descriptions.

Workers represent execution resources (LLM, Tool, System) with
declared capabilities for scheduler matching.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class WorkerStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


class WorkerType(str, Enum):
    LLM = "llm"
    TOOL = "tool"
    SYSTEM = "system"


@dataclass
class Worker:
    """A worker with declared capabilities for task matching.

    Attributes:
        id: Unique worker identifier.
        type: Worker category (llm, tool, system).
        status: Current worker status.
        capabilities: List of capability strings this worker provides.
        current_task: ID of the task currently being executed (if busy).
    """
    id: str
    type: WorkerType
    status: WorkerStatus = WorkerStatus.IDLE
    capabilities: list[str] = field(default_factory=list)
    current_task: Optional[str] = None

    def can_handle(self, required_capability: str) -> bool:
        """Check if this worker can handle a required capability.

        Args:
            required_capability: The capability string needed by a task.

        Returns:
            True if this worker's capabilities include the requirement.
        """
        return required_capability in self.capabilities

    def is_available(self) -> bool:
        """Check if worker is idle and ready for a task."""
        return self.status == WorkerStatus.IDLE and self.current_task is None

    def assign(self, task_id: str) -> None:
        """Assign a task to this worker, marking it busy."""
        self.current_task = task_id
        self.status = WorkerStatus.BUSY

    def release(self) -> None:
        """Release the worker, marking it idle."""
        self.current_task = None
        self.status = WorkerStatus.IDLE


# ── Predefined worker types ──────────────────────────────────

def create_llm_worker(worker_id: str) -> Worker:
    """Create a standard LLM worker with reasoning/planning/chat capabilities."""
    return Worker(
        id=worker_id,
        type=WorkerType.LLM,
        capabilities=["reasoning", "planning", "chat"],
    )


def create_tool_worker(worker_id: str) -> Worker:
    """Create a standard tool worker with shell/filesystem capabilities."""
    return Worker(
        id=worker_id,
        type=WorkerType.TOOL,
        capabilities=["shell", "filesystem"],
    )


def create_system_worker(worker_id: str) -> Worker:
    """Create a standard system worker with monitor/diagnostic capabilities."""
    return Worker(
        id=worker_id,
        type=WorkerType.SYSTEM,
        capabilities=["monitor", "diagnostic"],
    )
