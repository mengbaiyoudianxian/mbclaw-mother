"""MBOS Kernel v0.3 — Runtime Integration.

Integrates the full MBOS pipeline:
  User Request → Gateway → EventKernel → Governor Constitution Check
  → Planner → TaskGraph → Scheduler → Worker Selection
  → ExecutionEngine → ToolRuntime → Result → Audit → Memory

v0.3 upgrades:
  - TokenPool HTTP Client (port 8100) with local fallback
  - Global State Store (thread-safe)
  - Memory Bridge (Audit → Memory persistence)
  - Emergency Kill Switch (stop/resume)
  - Production Health Check

Maintains backward compatibility with V1 MotherRuntime interface.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from app.governor import Governor, ExecutionContext, GovernorDecision, RiskLevel, EmergencyControl
from app.planner import Planner, TaskGraph, TaskStatus
from app.scheduler import Scheduler, ScheduleResult
from app.worker import WorkerPool, create_llm_worker, create_tool_worker, create_system_worker
from app.token_pool import ResourceManager, ProviderInfo, ModelInfo, TokenPoolClient, TokenPoolStatus
from app.runtime.event_bus import EventBus
from app.runtime.event import (
    RequestEvent,
    ExecutionStartEvent,
    ExecutionFinishEvent,
    ExecutionFailedEvent,
    GovernorDenyEvent,
    PlannerCompleteEvent,
    SchedulerDispatchEvent,
    TaskCompleteEvent,
    AuditEvent,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Complete pipeline execution result.

    Attributes:
        success: Whether the pipeline completed successfully.
        goal: The original user goal.
        reply: Final response text.
        task_graph: The TaskGraph produced by Planner.
        schedule_results: Scheduling decisions for each task.
        error: Error message if pipeline failed.
        audit_log: List of audit event summaries.
    """
    success: bool = False
    goal: str = ""
    reply: str = ""
    task_graph: Optional[TaskGraph] = None
    schedule_results: list[ScheduleResult] = field(default_factory=list)
    error: str = ""
    audit_log: list[str] = field(default_factory=list)


class MBOSKernel:
    """MBOS Kernel v0.3 — Cognitive Layer + Runtime Integration.

    Full pipeline:
      Gateway → Governor → Planner → Scheduler → Workers → Audit → Memory

    v0.3 adds:
      - TokenPool HTTP Client (port 8100) with local fallback
      - Global State Store (thread-safe)
      - Memory Bridge (Audit → Memory persistence)
      - Emergency Kill Switch (stop/resume)

    Usage:
        kernel = MBOSKernel()
        result = kernel.process("检查服务器状态并生成报告", session_id=1)
        print(result.reply)
    """

    def __init__(self, token_pool_url: str = "http://127.0.0.1:8100"):
        # ── Global State ──
        from app.state import GlobalState
        self.state = GlobalState.get_instance()

        # ── EventBus ──
        self.event_bus = EventBus()
        self._setup_audit()

        # ── Governor (Constitution Layer) ──
        self.governor = Governor()

        # ── Emergency Control ──
        self.emergency = EmergencyControl(
            scheduler=None,  # Set after scheduler created
            worker_pool=None,  # Set after worker pool created
        )

        # ── Planner ──
        self.planner = Planner()

        # ── Worker Pool ──
        self.worker_pool = WorkerPool()
        self._bootstrap_workers()

        # ── Resource Manager (local fallback) ──
        self.resource_manager = ResourceManager()
        self._bootstrap_resources()

        # ── TokenPool HTTP Client ──
        self.token_pool = TokenPoolClient(
            resource_manager=self.resource_manager,
            base_url=token_pool_url,
        )

        # ── Scheduler ──
        self.scheduler = Scheduler(
            worker_pool=self.worker_pool,
            resource_manager=self.resource_manager,
            event_bus=self.event_bus,
        )

        # Wire emergency control to scheduler and worker pool
        self.emergency._scheduler = self.scheduler
        self.emergency._worker_pool = self.worker_pool

        # ── Memory Bridge ──
        from app.memory_bridge import MemoryBridge
        self.memory_bridge = MemoryBridge(event_bus=self.event_bus)

        # ── Update Global State ──
        self._sync_state()

        logger.info("MBOS Kernel v0.3 initialized — TokenPool: %s",
                    self.token_pool.status.value)

    def _bootstrap_workers(self) -> None:
        """Register default workers."""
        self.worker_pool.register(create_llm_worker("llm-1"))
        self.worker_pool.register(create_llm_worker("llm-2"))
        self.worker_pool.register(create_llm_worker("llm-3"))
        self.worker_pool.register(create_tool_worker("tool-1"))
        self.worker_pool.register(create_tool_worker("tool-2"))
        self.worker_pool.register(create_tool_worker("tool-3"))
        self.worker_pool.register(create_system_worker("sys-1"))
        self.worker_pool.register(create_system_worker("sys-2"))
        # Add diagnostic capability to system workers
        from app.worker.worker import Worker, WorkerType
        diag_worker = Worker(
            id="sys-diag", type=WorkerType.SYSTEM,
            capabilities=["monitor", "diagnostic"],
        )
        self.worker_pool.register(diag_worker)

    def _bootstrap_resources(self) -> None:
        """Register default LLM providers and models."""
        self.resource_manager.register_provider(ProviderInfo(
            provider="zhipu",
            models=[
                ModelInfo(name="glm-4", context="128K", cost="medium",
                          capabilities=["reasoning", "planning", "chat"]),
                ModelInfo(name="glm-4v", context="128K", cost="medium",
                          capabilities=["vision", "reasoning"]),
            ],
            quota_remaining=500,
        ))
        self.resource_manager.register_provider(ProviderInfo(
            provider="deepseek",
            models=[
                ModelInfo(name="deepseek-chat", context="64K", cost="low",
                          capabilities=["reasoning", "chat"]),
                ModelInfo(name="deepseek-coder", context="64K", cost="low",
                          capabilities=["code", "reasoning"]),
            ],
            quota_remaining=500,
        ))
        self.resource_manager.register_provider(ProviderInfo(
            provider="openai",
            models=[
                ModelInfo(name="gpt-4o", context="128K", cost="high",
                          capabilities=["vision", "reasoning", "planning", "chat"]),
            ],
            quota_remaining=100,
        ))

    def _setup_audit(self) -> None:
        """Register audit handlers for all pipeline events."""
        audit_entries: list[str] = []

        def audit_handler(event) -> None:
            entry = (
                f"[{event.event_type}] "
                f"session={event.session_id} "
                f"task={event.task_id}"
            )
            if hasattr(event, 'rule_hit') and event.rule_hit:
                entry += f" rule={event.rule_hit}"
            if hasattr(event, 'error') and event.error:
                entry += f" error={event.error}"
            audit_entries.append(entry)

        # Subscribe to all major event types
        from app.runtime.event import (
            RequestEvent, ExecutionStartEvent, ExecutionFinishEvent,
            ExecutionFailedEvent, GovernorDenyEvent, PlannerCompleteEvent,
            SchedulerDispatchEvent, TaskCompleteEvent,
        )
        for event_cls in [
            RequestEvent, ExecutionStartEvent, ExecutionFinishEvent,
            ExecutionFailedEvent, GovernorDenyEvent, PlannerCompleteEvent,
            SchedulerDispatchEvent, TaskCompleteEvent,
        ]:
            self.event_bus.subscribe(event_cls, audit_handler)

        self._audit_entries = audit_entries

    def _sync_state(self) -> None:
        """Sync GlobalState with current kernel state."""
        self.state.update({
            "current_goal": "",
            "active_tasks": [],
            "worker_status": [
                {
                    "worker_id": w.id,
                    "status": w.status.value,
                    "current_task": w.current_task or "",
                    "capabilities": w.capabilities,
                }
                for w in self.worker_pool.list_all()
            ],
            "token_status": {
                "connected": self.token_pool.is_connected,
                "status": self.token_pool.status.value,
            },
            "system_health": {"status": "healthy"},
        })

    def process(self, message: str, session_id: int = 0) -> PipelineResult:
        """Full cognitive pipeline execution.

        Args:
            message: User goal/message text.
            session_id: Session identifier.

        Returns:
            PipelineResult with success, reply, task_graph, and audit_log.
        """
        request_id = str(uuid.uuid4())
        audit_log = self._audit_entries
        audit_log.clear()

        # ── Phase 0: EventKernel — Request Received ──
        self.event_bus.publish(RequestEvent(
            event_id=str(uuid.uuid4()),
            request_id=request_id,
            session_id=session_id,
            payload={"message": message},
        ))

        # ── Phase 1: Governor Constitution Check ──
        self.event_bus.publish(ExecutionStartEvent(
            event_id=str(uuid.uuid4()),
            request_id=request_id,
            session_id=session_id,
        ))

        ctx = ExecutionContext(session_id=session_id, request_id=request_id)
        decision = self.governor.check(ctx, message)

        if not decision.allowed:
            self.event_bus.publish(GovernorDenyEvent(
                event_id=str(uuid.uuid4()),
                request_id=request_id,
                session_id=session_id,
                rule_hit=decision.rule_hit,
                risk_level=decision.risk_level.value,
            ))
            self.event_bus.publish(ExecutionFailedEvent(
                event_id=str(uuid.uuid4()),
                request_id=request_id,
                session_id=session_id,
                error=decision.reason,
            ))
            # Store memory
            self.memory_bridge.process_audit_log(list(audit_log), message)
            return PipelineResult(
                success=False,
                goal=message,
                reply=f"请求被拒绝: {decision.reason}",
                error=decision.reason,
                audit_log=list(audit_log),
            )

        # ── Emergency Stop Check ──
        if self.emergency.is_stopped():
            err_msg = f"系统紧急停止中: {self.emergency.stop_reason}"
            self.event_bus.publish(ExecutionFailedEvent(
                event_id=str(uuid.uuid4()),
                request_id=request_id,
                session_id=session_id,
                error=err_msg,
            ))
            self.memory_bridge.process_audit_log(list(audit_log), message)
            return PipelineResult(
                success=False,
                goal=message,
                reply=f"请求被拒绝: {err_msg}",
                error=err_msg,
                audit_log=list(audit_log),
            )

        # ── Phase 2: Planner — Goal Decomposition ──
        try:
            task_graph = self.planner.create_plan(message)
        except ValueError as e:
            self.event_bus.publish(ExecutionFailedEvent(
                event_id=str(uuid.uuid4()),
                request_id=request_id,
                session_id=session_id,
                error=str(e),
            ))
            return PipelineResult(
                success=False,
                goal=message,
                reply=f"规划失败: {e}",
                error=str(e),
                audit_log=list(audit_log),
            )

        self.event_bus.publish(PlannerCompleteEvent(
            event_id=str(uuid.uuid4()),
            request_id=request_id,
            session_id=session_id,
            task_count=len(task_graph.tasks),
            goal=task_graph.goal,
        ))

        # ── Phase 3: Scheduler — Task Dispatching ──
        schedule_results = self.scheduler.schedule_graph(task_graph)

        # Log task completions
        for task in task_graph.tasks:
            self.event_bus.publish(TaskCompleteEvent(
                event_id=str(uuid.uuid4()),
                request_id=request_id,
                session_id=session_id,
                task_id=task.id,
                task_status=task.status.value,
                payload={"task_name": task.name, "required_capability": task.required_capability},
            ))

        # ── Phase 4: Audit + Result ──
        self.event_bus.publish(ExecutionFinishEvent(
            event_id=str(uuid.uuid4()),
            request_id=request_id,
            session_id=session_id,
            payload={
                "goal": task_graph.goal,
                "task_count": len(task_graph.tasks),
                "scheduled_count": sum(1 for r in schedule_results if r.success),
            },
        ))

        # ── Memory Bridge: persist experience ──
        self.memory_bridge.process_audit_log(list(audit_log), task_graph.goal)

        # ── Sync state ──
        self.state.set("current_goal", task_graph.goal)
        self.state.set("active_tasks", [t.id for t in task_graph.tasks])

        # Build reply
        scheduled_count = sum(1 for r in schedule_results if r.success)
        failed_schedules = [r for r in schedule_results if not r.success]

        if failed_schedules:
            reply = (
                f"任务规划完成: {task_graph.goal}\n"
                f"共 {len(task_graph.tasks)} 个任务, "
                f"成功调度 {scheduled_count} 个\n"
                f"失败: {'; '.join(r.reason for r in failed_schedules)}"
            )
        else:
            reply = (
                f"任务规划完成: {task_graph.goal}\n"
                f"共 {len(task_graph.tasks)} 个任务, "
                f"全部调度成功"
            )

        return PipelineResult(
            success=len(failed_schedules) == 0,
            goal=task_graph.goal,
            reply=reply,
            task_graph=task_graph,
            schedule_results=schedule_results,
            audit_log=list(audit_log),
        )

    def health_report(self) -> dict:
        """Generate a health report for all kernel components.

        Returns:
            Dict with component statuses.
        """
        tp_status = self.token_pool.status.value
        tp_connected = self.token_pool.is_connected
        return {
            "kernel": "MBOS Kernel v0.3",
            "governor": {
                "rules": len(self.governor.list_rules()),
                "status": "active",
                "emergency_stop": self.emergency.is_stopped(),
                "stop_reason": self.emergency.stop_reason,
            },
            "planner": {
                "status": "active",
                "strategies": "12 pattern-based",
            },
            "workers": {
                "total": len(self.worker_pool.list_all()),
                "available": len(self.worker_pool.list_available()),
            },
            "token_pool": {
                "connected": tp_connected,
                "status": tp_status,
                "last_error": self.token_pool.last_error if not tp_connected else "",
                "providers": len(self.resource_manager.list_providers()),
                "total_models": sum(
                    len(p.models) for p in self.resource_manager.list_providers()
                ),
            },
            "scheduler": {
                "history": len(self.scheduler.get_scheduling_log()),
            },
            "event_bus": {
                "status": "active",
            },
            "memory": {
                "entries": self.memory_bridge.memory_store.size(),
            },
            "state": {
                "current_goal": self.state.get("current_goal", ""),
                "active_tasks": self.state.get("active_tasks", []),
            },
        }
