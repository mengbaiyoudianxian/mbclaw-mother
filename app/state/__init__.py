"""MBOS State — thread-safe global state store.

Provides a single source of truth for MBOS runtime state including:
  - current_goal, active_tasks, worker_status
  - token_status, system_health, last_decision
"""
from __future__ import annotations

import copy
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class SystemHealth:
    status: str = "healthy"
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: dict = field(default_factory=dict)


@dataclass
class TokenStatus:
    provider: str = ""
    model: str = ""
    quota_remaining: int = 0
    connected: bool = False


@dataclass
class WorkerStatusSnapshot:
    worker_id: str = ""
    status: str = ""
    current_task: str = ""
    capabilities: list = field(default_factory=list)


@dataclass
class StateSnapshot:
    """Immutable snapshot of the full MBOS state."""
    current_goal: str = ""
    active_tasks: list[str] = field(default_factory=list)
    worker_status: list[WorkerStatusSnapshot] = field(default_factory=list)
    token_status: TokenStatus = field(default_factory=TokenStatus)
    system_health: SystemHealth = field(default_factory=SystemHealth)
    last_decision: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    emergency_stop: bool = False


class GlobalState:
    """Thread-safe singleton for MBOS global state.

    All reads and writes are protected by a reentrant lock.
    Provides get(), set(), and snapshot() for all state components.
    """

    _instance: Optional["GlobalState"] = None
    _class_lock = threading.Lock()

    def __init__(self):
        self._lock = threading.RLock()
        self._data: dict[str, Any] = {
            "current_goal": "",
            "active_tasks": [],
            "worker_status": [],
            "token_status": TokenStatus(),
            "system_health": SystemHealth(),
            "last_decision": {},
            "emergency_stop": False,
        }

    @classmethod
    def get_instance(cls) -> "GlobalState":
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._class_lock:
            cls._instance = None

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return copy.deepcopy(self._data.get(key, default))

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = copy.deepcopy(value)

    def update(self, updates: dict) -> None:
        with self._lock:
            for key, value in updates.items():
                self._data[key] = copy.deepcopy(value)

    def snapshot(self) -> StateSnapshot:
        with self._lock:
            return StateSnapshot(
                current_goal=str(self._data.get("current_goal", "")),
                active_tasks=list(self._data.get("active_tasks", [])),
                worker_status=list(self._data.get("worker_status", [])),
                token_status=copy.deepcopy(self._data.get("token_status", TokenStatus())),
                system_health=copy.deepcopy(self._data.get("system_health", SystemHealth())),
                last_decision=dict(self._data.get("last_decision", {})),
                timestamp=datetime.now(timezone.utc),
                emergency_stop=bool(self._data.get("emergency_stop", False)),
            )

    def is_emergency_stop(self) -> bool:
        return bool(self.get("emergency_stop", False))

    @property
    def keys(self) -> list:
        with self._lock:
            return list(self._data.keys())


def get_state() -> GlobalState:
    """Get the singleton GlobalState instance."""
    return GlobalState.get_instance()
