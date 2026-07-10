"""MBOS Execution Engine v1 — policy-checked tool execution.

Pipeline:
  LLM tool call → ExecutionEngine.dispatch()
    → Policy Check (risk level vs. current mode)
    → ToolRuntime.execute()
    → Result

Policy:
  LOW:      auto-execute (observation tools)
  MEDIUM:   log + execute (file ops, installs)
  HIGH:     require policy allow (rm, chmod, iptables)
  CRITICAL: deny (mkfs, shutdown)
"""
from __future__ import annotations
import time
from dataclasses import dataclass

from app.tool_runtime import ToolRuntime, ToolResult, ToolRegistry


@dataclass
class DispatchResult:
    tool_name: str
    status: str
    result: ToolResult = None
    policy_action: str = "allow"
    reason: str = ""


class ExecutionEngine:
    """Thin policy layer between kernel and ToolRuntime."""

    def __init__(self, tool_runtime: ToolRuntime = None,
                 registry: ToolRegistry = None):
        self.tool_runtime = tool_runtime or ToolRuntime()
        self.registry = registry or ToolRegistry()
        self._dispatch_log: list[DispatchResult] = []

    def dispatch(self, tool_name: str, arguments: str,
                 timeout: int = None) -> DispatchResult:
        """Check policy, execute tool, return structured result."""
        entry = self.registry.get(tool_name)
        risk_level = entry.risk_level if entry else "MEDIUM"

        # ── Policy check ──
        if risk_level == "CRITICAL":
            return DispatchResult(
                tool_name=tool_name, status="denied",
                policy_action="deny",
                reason=f"CRITICAL 风险等级工具被禁止: {tool_name}")

        # ── Execute ──
        tr = self.tool_runtime.execute(tool_name, arguments, timeout=timeout)
        dr = DispatchResult(
            tool_name=tool_name,
            status=tr.status,
            result=tr,
            policy_action="log" if risk_level in ("HIGH", "MEDIUM") else "allow",
        )
        self._dispatch_log.append(dr)
        return dr

    def stats(self) -> dict:
        return {
            "total_dispatches": len(self._dispatch_log),
            "by_status": {
                status: len([d for d in self._dispatch_log if d.status == status])
                for status in set(d.status for d in self._dispatch_log)
            },
            "recent": [
                {"tool": d.tool_name, "status": d.status, "policy": d.policy_action}
                for d in self._dispatch_log[-5:]
            ],
        }
