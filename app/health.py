"""MBOS Health Check — production health endpoint.

GET /health/full returns comprehensive system status including:
  kernel, governor, planner, scheduler, workers, token_pool,
  memory, tools, and emergency_stop status.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class HealthReport:
    """Full MBOS system health report.

    Attributes:
        status: Overall system status (healthy, degraded, emergency_stop).
        kernel: Kernel version and status.
        governor: Governor rules count and status.
        planner: Planner status.
        scheduler: Scheduler history and status.
        workers: Worker pool summary.
        token_pool: TokenPool connection and provider status.
        memory: Memory store statistics.
        tools: Placeholder for tool runtime status.
        emergency_stop: Whether emergency stop is active.
        timestamp: When this report was generated.
    """
    status: str = "unknown"
    kernel: dict = field(default_factory=dict)
    governor: dict = field(default_factory=dict)
    planner: dict = field(default_factory=dict)
    scheduler: dict = field(default_factory=dict)
    workers: dict = field(default_factory=dict)
    token_pool: dict = field(default_factory=dict)
    memory: dict = field(default_factory=dict)
    tools: dict = field(default_factory=dict)
    emergency_stop: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HealthChecker:
    """Generates full system health reports for MBOS.

    Aggregates status from all kernel components into a single
    HealthReport.

    Usage:
        hc = HealthChecker(kernel, memory_bridge)
        report = hc.full_health()
    """

    def __init__(self, kernel=None, memory_bridge=None, token_pool_client=None):
        self._kernel = kernel
        self._memory_bridge = memory_bridge
        self._token_pool_client = token_pool_client

    def full_health(self) -> HealthReport:
        """Generate a comprehensive health report.

        Returns:
            HealthReport with all component statuses.
        """
        from app.state import get_state, StateSnapshot

        state = get_state()
        snap = state.snapshot()
        is_emergency = snap.emergency_stop

        # ── Kernel ──
        kernel_info = {
            "status": "active",
            "version": "v0.3",
        }
        if self._kernel:
            kernel_info.update(self._kernel.health_report() if hasattr(self._kernel, 'health_report') else {})

        # ── Governor ──
        governor_info = {"status": "active", "rules": 5}
        if self._kernel and hasattr(self._kernel, 'governor'):
            governor_info["rules"] = len(self._kernel.governor.list_rules())

        # ── Planner ──
        planner_info = {"status": "active"}

        # ── Scheduler ──
        scheduler_info = {
            "status": "active",
            "history": 0,
        }
        if self._kernel and hasattr(self._kernel, 'scheduler'):
            scheduler_info["history"] = len(self._kernel.scheduler.get_scheduling_log())

        # ── Workers ──
        workers_info = {
            "total": 0,
            "available": 0,
            "status": "active",
        }
        if self._kernel and hasattr(self._kernel, 'worker_pool'):
            workers_info["total"] = len(self._kernel.worker_pool.list_all())
            workers_info["available"] = len(self._kernel.worker_pool.list_available())

        # ── TokenPool ──
        token_pool_info = {"status": "offline", "providers": 0}
        if self._token_pool_client:
            token_pool_info["connected"] = self._token_pool_client.is_connected
            token_pool_info["status"] = self._token_pool_client.status.value
            token_pool_info["last_error"] = self._token_pool_client.last_error
            token_pool_info["providers"] = len(
                self._token_pool_client._resource_manager.list_providers()
            )
        elif self._kernel and hasattr(self._kernel, 'resource_manager'):
            token_pool_info["providers"] = len(self._kernel.resource_manager.list_providers())
            token_pool_info["status"] = "local_only"

        # ── Memory ──
        memory_info = {"entries": 0, "status": "active"}
        if self._memory_bridge and hasattr(self._memory_bridge, 'memory_store'):
            memory_info["entries"] = self._memory_bridge.memory_store.size()
            memory_info["recent_failures"] = len(
                self._memory_bridge.memory_store.recent_failures()
            )
            memory_info["recent_successes"] = len(
                self._memory_bridge.memory_store.recent_successes()
            )

        # ── Tools ──
        tools_info = {"status": "active", "runtime": "v1.2"}

        # ── Overall status ──
        if is_emergency:
            overall = "emergency_stop"
        elif not token_pool_info.get("connected", True) and token_pool_info.get("status") == "offline":
            overall = "degraded"
        else:
            overall = "healthy"

        return HealthReport(
            status=overall,
            kernel=kernel_info,
            governor=governor_info,
            planner=planner_info,
            scheduler=scheduler_info,
            workers=workers_info,
            token_pool=token_pool_info,
            memory=memory_info,
            tools=tools_info,
            emergency_stop=is_emergency,
        )

    def quick_health(self) -> dict:
        """Lightweight health check (fast).

        Returns:
            Dict with status, emergency_stop, and uptime.
        """
        from app.state import get_state
        state = get_state()
        return {
            "status": "emergency_stop" if state.is_emergency_stop() else "running",
            "emergency_stop": state.is_emergency_stop(),
        }
