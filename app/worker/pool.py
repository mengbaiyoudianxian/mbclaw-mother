"""MBOS Worker — worker pool for capability-based dispatch.

WorkerPool manages a collection of Workers and provides
capability-based matching for the Scheduler.
"""
from __future__ import annotations

import logging
from typing import Optional

from .worker import Worker, WorkerStatus

logger = logging.getLogger(__name__)


class WorkerPool:
    """Manages a pool of Workers with capability-based dispatch.

    Workers are registered by ID. The Scheduler queries the pool
    to find the best worker for a given task capability.

    Usage:
        pool = WorkerPool()
        pool.register(create_llm_worker("llm-1"))
        worker = pool.find_best("reasoning")
    """

    def __init__(self):
        self._workers: dict[str, Worker] = {}

    def register(self, worker: Worker) -> None:
        """Register a worker in the pool."""
        self._workers[worker.id] = worker
        logger.info("WorkerPool: registered %s [%s] caps=%s",
                    worker.id, worker.type.value, worker.capabilities)

    def unregister(self, worker_id: str) -> None:
        """Remove a worker from the pool."""
        self._workers.pop(worker_id, None)

    def find_best(self, required_capability: str) -> Optional[Worker]:
        """Find the best available worker for a required capability.

        Priority: IDLE workers only. Among candidates, prefers the
        one with the fewest capabilities (most specialized).

        Args:
            required_capability: The capability string needed.

        Returns:
            Best matching Worker or None if no match found.
        """
        candidates = [
            w for w in self._workers.values()
            if w.is_available() and w.can_handle(required_capability)
        ]

        if not candidates:
            logger.debug(
                "WorkerPool: no idle worker for capability '%s'",
                required_capability,
            )
            return None

        # Prefer most specialized worker (fewest capabilities)
        best = min(candidates, key=lambda w: len(w.capabilities))
        logger.debug(
            "WorkerPool: selected %s for capability '%s'",
            best.id, required_capability,
        )
        return best

    def find_all(self, required_capability: str) -> list[Worker]:
        """Find all workers (including busy) matching a capability."""
        return [
            w for w in self._workers.values()
            if w.can_handle(required_capability)
        ]

    def list_available(self) -> list[Worker]:
        """List all idle workers."""
        return [w for w in self._workers.values() if w.is_available()]

    def list_all(self) -> list[Worker]:
        """List all workers regardless of status."""
        return list(self._workers.values())

    def get(self, worker_id: str) -> Optional[Worker]:
        """Get a worker by ID."""
        return self._workers.get(worker_id)

    def release_all(self) -> None:
        """Release all busy workers back to idle."""
        for worker in self._workers.values():
            if worker.status == WorkerStatus.BUSY:
                worker.release()
