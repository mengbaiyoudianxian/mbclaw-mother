"""MBOS Governor Emergency Control — Kill Switch.

Provides immediate stop of Scheduler + Worker new task dispatch
while preserving Audit logging. Emergency stop and resume.

Exposes:
  POST /control/emergency_stop  — halt new task dispatch
  POST /control/resume          — resume normal operation
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.state import get_state

logger = logging.getLogger(__name__)


@dataclass
class ControlResult:
    """Result of an emergency control operation.

    Attributes:
        success: Whether the operation completed.
        action: The action taken (emergency_stop, resume).
        message: Human-readable result message.
        timestamp: When the action was taken.
        state_before: Snapshot of state before action.
        state_after: Snapshot of state after action.
    """
    success: bool = False
    action: str = ""
    message: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    state_before: dict = field(default_factory=dict)
    state_after: dict = field(default_factory=dict)


class EmergencyControl:
    """Governor Emergency Control — Kill Switch.

    Manages the emergency_stop flag in GlobalState. When active:
      - Scheduler must not dispatch new tasks
      - WorkerPool must not assign new work
      - Audit logging continues
      - Pipeline returns "emergency_stop" error for new requests

    Usage:
        ctrl = EmergencyControl()
        result = ctrl.emergency_stop(reason="TokenPool quota exhausted")
        # ... investigation ...
        result = ctrl.resume()
    """

    def __init__(self, scheduler=None, worker_pool=None):
        self._scheduler = scheduler
        self._worker_pool = worker_pool
        self._stop_reason = ""
        self._stop_count = 0

    def emergency_stop(self, reason: str = "") -> ControlResult:
        """Immediately halt all new task dispatch.

        Sets emergency_stop flag in GlobalState. Existing tasks
        continue to execute. Audit logging continues.

        Args:
            reason: Human-readable reason for the emergency stop.

        Returns:
            ControlResult with action details.
        """
        state = get_state()
        state_before = {
            "emergency_stop": state.get("emergency_stop"),
            "active_tasks": state.get("active_tasks", []),
        }

        state.set("emergency_stop", True)
        self._stop_reason = reason
        self._stop_count += 1

        # Release all busy workers to prevent new assignments
        if self._worker_pool:
            self._worker_pool.release_all()
            logger.warning("EmergencyControl: released all workers")

        state_after = {
            "emergency_stop": True,
            "active_tasks": state.get("active_tasks", []),
        }

        logger.critical(
            "EmergencyControl: EMERGENCY STOP #%d — %s",
            self._stop_count, reason,
        )

        return ControlResult(
            success=True,
            action="emergency_stop",
            message=f"Emergency stop #{self._stop_count} activated: {reason}",
            state_before=state_before,
            state_after=state_after,
        )

    def resume(self) -> ControlResult:
        """Resume normal operation after emergency stop.

        Clears emergency_stop flag. Workers can accept new tasks.

        Returns:
            ControlResult with action details.
        """
        state = get_state()
        state_before = {
            "emergency_stop": state.get("emergency_stop"),
        }

        state.set("emergency_stop", False)
        self._stop_reason = ""

        state_after = {
            "emergency_stop": False,
        }

        logger.info("EmergencyControl: RESUME — normal operation restored")

        return ControlResult(
            success=True,
            action="resume",
            message="Normal operation resumed",
            state_before=state_before,
            state_after=state_after,
        )

    def is_stopped(self) -> bool:
        """Check if emergency stop is currently active."""
        return get_state().is_emergency_stop()

    @property
    def stop_reason(self) -> str:
        return self._stop_reason

    @property
    def stop_count(self) -> int:
        return self._stop_count
