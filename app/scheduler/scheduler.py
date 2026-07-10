"""MBOS Scheduler v2 — multi-factor task scheduling.

Scheduler matches Tasks to Workers and Models using:
  1. Task.required_capability → Worker.capabilities
  2. Task.priority → Worker selection order
  3. Task type → Model capability via ResourceManager
  4. Worker availability → Only IDLE workers

V2 upgrades from V1:
  - Capability-based worker matching
  - ResourceManager integration for model selection
  - Priority-aware dispatch
  - SchedulerDispatchEvent emission
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ScheduleResult:
    """Result of a scheduler dispatch decision.

    Attributes:
        task_id: The task being scheduled.
        worker_id: The assigned worker ID (empty if no worker found).
        provider: The selected LLM provider.
        model: The selected LLM model.
        success: Whether a valid schedule was found.
        reason: Explanation for success or failure.
    """
    task_id: str = ""
    worker_id: str = ""
    provider: str = ""
    model: str = ""
    success: bool = False
    reason: str = ""
    metadata: dict = field(default_factory=dict)


class Scheduler:
    """V2 multi-factor scheduler.

    Matches tasks to workers and models based on capability,
    priority, availability, and resource scores.

    Usage:
        scheduler = Scheduler(worker_pool, resource_manager, event_bus)
        result = scheduler.schedule_task(task)
        if result.success:
            print(f"Task {task.id} → Worker {result.worker_id} via {result.model}")
    """

    def __init__(self, worker_pool=None, resource_manager=None, event_bus=None):
        from app.worker.pool import WorkerPool
        from app.token_pool.resource_manager import ResourceManager
        self._worker_pool = worker_pool or WorkerPool()
        self._resource_manager = resource_manager or ResourceManager()
        self._event_bus = event_bus
        self._scheduling_log: list[ScheduleResult] = []

    def schedule_task(self, task) -> ScheduleResult:
        """Schedule a single task to the best worker and model.

        Decision pipeline:
          1. Find worker matching task.required_capability
          2. Select model via ResourceManager based on task type
          3. If both found, assign task to worker

        Args:
            task: A Task with id, required_capability, type, priority.

        Returns:
            ScheduleResult with worker_id, provider, model, and success flag.
        """
        capability = task.required_capability

        # ── Step 1: Find worker ──
        worker = self._worker_pool.find_best(capability)
        if worker is None:
            result = ScheduleResult(
                task_id=task.id,
                success=False,
                reason=f"no available worker for capability '{capability}'",
            )
            self._scheduling_log.append(result)
            return result

        # ── Step 2: Select model ──
        task_req = {"capability": capability}
        task_capability_map = {
            "reasoning": "reasoning",
            "analysis": "reasoning",
            "planning": "planning",
            "chat": "chat",
            "report": "reasoning",
            "system_observe": "reasoning",
            "action": "reasoning",
            "diagnostic": "reasoning",
        }
        model_capability = task_capability_map.get(task.type, "reasoning")
        task_req["capability"] = model_capability

        model_selection = self._resource_manager.select_model(task_req)
        if model_selection is None:
            result = ScheduleResult(
                task_id=task.id,
                worker_id=worker.id,
                success=False,
                reason=f"no model available for requirement {task_req}",
            )
            self._scheduling_log.append(result)
            return result

        provider, model = model_selection

        # ── Step 3: Assign worker ──
        worker.assign(task.id)
        result = ScheduleResult(
            task_id=task.id,
            worker_id=worker.id,
            provider=provider,
            model=model,
            success=True,
            reason=f"task '{task.id}' → worker '{worker.id}' via {provider}/{model}",
            metadata={
                "capability": capability,
                "model_capability": model_capability,
                "priority": task.priority,
            },
        )
        self._scheduling_log.append(result)

        # ── Emit event ──
        if self._event_bus:
            from app.runtime.event import SchedulerDispatchEvent
            import uuid
            self._event_bus.publish(SchedulerDispatchEvent(
                event_id=str(uuid.uuid4()),
                task_id=task.id,
                worker_id=worker.id,
                model=model,
                capability=capability,
                payload={"provider": provider, "task_type": task.type},
            ))

        logger.info("Scheduler: %s", result.reason)
        return result

    def schedule_graph(self, task_graph) -> list[ScheduleResult]:
        """Schedule all ready tasks in a TaskGraph in topological order.

        Args:
            task_graph: TaskGraph with tasks to schedule.

        Returns:
            List of ScheduleResult for each scheduled task.
        """
        results: list[ScheduleResult] = []
        try:
            ordered = task_graph.topological_order()
        except RuntimeError:
            ordered = task_graph.tasks

        for task in ordered:
            result = self.schedule_task(task)
            results.append(result)
        return results

    def get_scheduling_log(self) -> list[ScheduleResult]:
        """Return the scheduling history."""
        return list(self._scheduling_log)
