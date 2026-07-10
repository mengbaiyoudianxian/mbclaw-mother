"""MBOS Worker Pool v1 — managed execution workers.

Worker types:
  LLMWorker   — makes LLM API calls
  ToolWorker  — executes tools via ToolRuntime
  SystemWorker — background maintenance (health checks, memory cleanup)

States: idle → busy → idle | failed
"""
import time, threading
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class WorkerType(str, Enum):
    LLM = "llm"
    TOOL = "tool"
    SYSTEM = "system"


class WorkerStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    FAILED = "failed"


@dataclass
class Worker:
    wid: str
    wtype: WorkerType
    status: WorkerStatus = WorkerStatus.IDLE
    current_task: str = ""
    started_at: float = 0.0
    error: str = ""
    call_count: int = 0
    error_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.wid, "type": self.wtype.value,
            "status": self.status.value,
            "current_task": self.current_task or "",
            "calls": self.call_count, "errors": self.error_count,
        }


class WorkerPool:
    """Manages a pool of typed workers with idle/busy/failed tracking."""

    def __init__(self):
        self._workers: dict[str, Worker] = {}
        self._lock = threading.Lock()
        self._next_id = 0

    def create(self, wtype: WorkerType, count: int = 1) -> list[Worker]:
        """Create workers of a given type."""
        created = []
        with self._lock:
            for _ in range(count):
                self._next_id += 1
                wid = f"{wtype.value}-{self._next_id:03d}"
                w = Worker(wid=wid, wtype=wtype)
                self._workers[wid] = w
                created.append(w)
        return created

    def acquire(self, wtype: WorkerType) -> Optional[Worker]:
        """Find an idle worker of the given type, mark as busy."""
        with self._lock:
            for w in self._workers.values():
                if w.wtype == wtype and w.status == WorkerStatus.IDLE:
                    w.status = WorkerStatus.BUSY
                    w.started_at = time.time()
                    w.call_count += 1
                    return w
        return None

    def release(self, wid: str, error: str = ""):
        """Release a worker back to idle or mark as failed."""
        with self._lock:
            w = self._workers.get(wid)
            if w:
                if error:
                    w.status = WorkerStatus.FAILED
                    w.error = error
                    w.error_count += 1
                else:
                    w.status = WorkerStatus.IDLE
                    w.current_task = ""

    def mark_failed(self, wid: str, error: str):
        self.release(wid, error)

    def status(self) -> dict:
        with self._lock:
            workers = [w.to_dict() for w in self._workers.values()]
            by_type: dict[str, dict] = {}
            for w in self._workers.values():
                t = w.wtype.value
                if t not in by_type:
                    by_type[t] = {"total": 0, "idle": 0, "busy": 0, "failed": 0}
                by_type[t]["total"] += 1
                by_type[t][w.status.value] += 1
            return {
                "workers": workers,
                "by_type": by_type,
                "total": len(workers),
                "idle": sum(1 for w in self._workers.values() if w.status == WorkerStatus.IDLE),
                "busy": sum(1 for w in self._workers.values() if w.status == WorkerStatus.BUSY),
                "failed": sum(1 for w in self._workers.values() if w.status == WorkerStatus.FAILED),
            }

    def cleanup_failed(self):
        """Reset failed workers to idle."""
        with self._lock:
            for w in self._workers.values():
                if w.status == WorkerStatus.FAILED:
                    w.status = WorkerStatus.IDLE
                    w.error = ""
