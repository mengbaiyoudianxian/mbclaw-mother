"""MBOS Runtime Kernel v1 — single entry point.

MotherRuntime is the ONLY execution entry point for MBOS.
Context is delegated to ContextEngine (Task 16).
Memory is delegated to Memory module (Task 17).
Capability is delegated to Capability module (Task 19).

DO NOT add: prompt building, memory storage, LLM routing, policy checks,
  tool execution, tool registration.
Those belong to ContextEngine/Memory/Scheduler/Governor/Capability.
"""
import re
import uuid

from .state import ExecutionContext, ExecutionResult, ExecutionStatus
from .lifecycle import Lifecycle
from .event import (
    Event,
    RequestEvent,
    ExecutionStartEvent,
    ExecutionFinishEvent,
    ExecutionFailedEvent,
    StateChangedEvent,
)
from .event_bus import EventBus
from app.capability import Capability, ToolDefinition
from app.context import ContextEngine, WorkingMemory
from app.governor.governor import Governor
from app.memory import Memory
from app.planner import Planner
from app.scheduler.scheduler import Scheduler
from app.tool_runtime import ToolRuntime, ToolRegistry

# ── Tool regex (kernel-level: used in _execute for LLM output parsing) ──
TOOL_RE = re.compile(r'<tool>(.*?)</tool>\s*<content>(.*?)</content>', re.DOTALL)
THINK_RE = re.compile(r'<thinking>(.*?)</thinking>', re.DOTALL)


# ── MotherRuntime Kernel ────────────────────────────────────
class MotherRuntime:
    """MBOS v1 — single execution entry point.

    All execution paths MUST enter through run().
    Temporary compat: LLM/Tool/Prompt logic preserved as-is.
    """

    def __init__(self, db_session_factory=None):
        self._sessions: dict[int, WorkingMemory] = {}
        # EventBus is per-instance — NOT a global singleton.
        # Each MotherRuntime owns its own bus.
        self.event_bus: EventBus = EventBus()
        # Governor — execution gate (Task 13)
        self.governor = Governor()
        # Scheduler — LLM dispatch (Task 14)
        self.scheduler = Scheduler()
        # ContextEngine — prompt/context assembly (Task 16)
        self.context_engine = ContextEngine()
        # Memory — long-term memory (Task 17)
        self.memory = Memory()
        # Planner — goal decomposition (Task 18)
        self.planner = Planner()
        # Capability — tool registry and execution (Task 19)
        self.capability = Capability()
        # ToolRegistry must be created BEFORE _bootstrap_tools (which registers into it)
        self.tool_registry = ToolRegistry()
        self.tool_runtime = ToolRuntime(capability=self.capability,
                                        registry=self.tool_registry)
        self._bootstrap_tools(db_session_factory)
        # Gateway — unified entry layer (Task 20)
        # Lazy import to avoid circular: gateway/router.py imports app.runtime
        from app.gateway import Gateway
        self.gateway = Gateway(self)

    def _get_session(self, sid: int) -> WorkingMemory:
        if sid not in self._sessions:
            wm = WorkingMemory()
            self._sessions[sid] = wm
        return self._sessions[sid]

    def run(self, message: str, session_id: int = 0,
            max_turns: int = 5, llm_client=None) -> ExecutionResult:
        """Single entry point. All callers → this method.

        Args:
            message: User message text.
            session_id: Session identifier (default 0 = auto).
            max_turns: Max agent loop turns.
            llm_client: Optional LLMClient for backward compat (agent_run path).
                        If provided, Scheduler uses it for LLM calls.

        Returns:
            ExecutionResult with .output, .success, .error, .metadata.
        """
        ctx = ExecutionContext(
            request_id=str(uuid.uuid4()),
            session_id=session_id,
        )
        request_id = ctx.request_id

        # ── Event: Request received ──
        self.event_bus.emit(RequestEvent(
            event_id=str(uuid.uuid4()),
            request_id=request_id,
            session_id=session_id,
            payload={"message": message, "max_turns": max_turns},
        ))

        Lifecycle.receive(ctx)

        # ── Event: Execution started ──
        self.event_bus.emit(ExecutionStartEvent(
            event_id=str(uuid.uuid4()),
            request_id=request_id,
            session_id=session_id,
        ))

        # ── Governor check (Task 13) ──
        decision = self.governor.check(ctx, message)
        if not decision.allow:
            fail_result = Lifecycle.fail(ctx, decision.reason)
            self.event_bus.emit(ExecutionFailedEvent(
                event_id=str(uuid.uuid4()),
                request_id=request_id,
                session_id=session_id,
                error=decision.reason,
            ))
            return fail_result

        try:
            result = self._execute(message, session_id, max_turns, llm_client)
            exec_result = Lifecycle.collect(ctx, output=result.get("reply", ""),
                                            error=result.get("error"))

            # ── Event: Execution finished ──
            self.event_bus.emit(ExecutionFinishEvent(
                event_id=str(uuid.uuid4()),
                request_id=request_id,
                session_id=session_id,
                result=exec_result,
                payload=result,
            ))

            return exec_result
        except Exception as e:
            fail_result = Lifecycle.fail(ctx, str(e))

            # ── Event: Execution failed ──
            self.event_bus.emit(ExecutionFailedEvent(
                event_id=str(uuid.uuid4()),
                request_id=request_id,
                session_id=session_id,
                error=str(e),
            ))

            return fail_result

    def _execute(self, message: str, session_id: int,
                 max_turns: int, llm_client=None) -> dict:
        """Internal execution loop — ToolRuntime v1.1 integrated."""
        wm = self._get_session(session_id)
        wm.add("user", message)

        # Create plan via Planner (Task 18)
        plan = self.planner.create_plan(message)

        # Prime memory via Memory module (Task 17)
        try:
            hits = self.memory.query(session_id, limit=3)
            if hits:
                wm.set_recall([f"[#{r.session_id}] {r.content[:200]}" for r in hits])
        except Exception:
            pass

        tools_used = []
        tool_details = []
        final_reply = ""
        error_count = 0
        consecutive_tool_errors = 0

        for turn in range(max_turns):
            # LLM call: dispatch via Scheduler (context from ContextEngine)
            raw, last_err = self.scheduler.dispatch(
                self.context_engine.build(message, session_id, wm),
                llm_client=llm_client)

            if raw is None:
                error_count += 1
                if error_count >= 2:
                    final_reply = f"LLM调用失败: {last_err}"
                    break
                continue

            # Parse tools
            tms = [(m.group(1).strip(), m.group(2).strip())
                   for m in TOOL_RE.finditer(raw)]
            clean = TOOL_RE.sub('', raw).strip()
            clean = THINK_RE.sub('', clean).strip()

            if not tms:
                final_reply = clean
                break

            results = []
            for tname, tcontent in tms[:3]:
                tools_used.append(tname)
                # ── ToolRuntime v1.1: timeout, structured result, error recovery ──
                tr = self.tool_runtime.execute(tname, tcontent)
                tool_details.append({
                    "tool": tname,
                    "status": tr.status,
                    "execution_time": tr.execution_time,
                })
                results.append(f"[{tname}] 结果:\n{tr.to_display()}")

                # Error recovery: classify and decide
                if tr.status != "success":
                    consecutive_tool_errors += 1
                    if tr.status == "timeout":
                        results.append(f"[系统] {tname} 超时，请尝试简化命令或分步执行。")
                    elif tr.status == "blocked":
                        results.append(f"[系统] {tname} 被安全策略拦截，请使用其他方式。")
                    else:
                        results.append(f"[系统] {tname} 执行失败({tr.error_type}): {tr.error[:200]}")
                    if consecutive_tool_errors >= 3:
                        wm.add("assistant", clean or "[工具调用]")
                        wm.add("user", "\n".join(results))
                        final_reply = f"多次工具调用失败，已停止。最近错误: {tr.error[:200]}"
                        break
                else:
                    consecutive_tool_errors = 0

            wm.add("assistant", clean or "[工具调用]")
            wm.add("user", "工具执行结果:\n" + "\n".join(results))

            if clean:
                final_reply = clean
                break

        if not final_reply:
            final_reply = "收到（母体-小梦已读）"

        wm.add("assistant", final_reply)
        turn_count = turn + 1 if 'turn' in dir() else 0
        return {"reply": final_reply, "turns": turn_count,
                "tool_calls": tools_used,
                "tool_details": tool_details}

    def _bootstrap_tools(self, db_session_factory):
        """Register tool handlers into Capability (Task 19).

        Three handler categories:
          1. Skill-based: github_*, ssh_exec → app.skills.execute_skill
          2. External API placeholders → app.skills.api_placeholder
          3. DB-based fallback: all others → app.tools.execute
        """
        # ── Register all tools in ToolRegistry ──
        _core_tools = ["run_command", "read_file", "write_file", "edit_file",
                       "list_directory", "search_memory"]
        for tname in _core_tools:
            self.tool_registry.register(tname, f"系统工具: {tname}", "root")

        # ── Skill-based tools ──
        def _make_skill_handler(name: str):
            def _handler(arg: str) -> str:
                from app.skills import execute_skill
                return execute_skill(name, arg)[:2000]
            return _handler

        self.capability.register(ToolDefinition(
            name="ssh_exec", description="SSH远程执行",
            handler=_make_skill_handler("ssh_exec")))

        _github_tools = [
            "github_search_code", "github_list_repos", "github_get_pr",
            "github_create_pr", "github_list_issues", "github_create_issue",
            "github_get_file", "github_list_workflows", "github_workflow_runs",
            "github_pr_review", "github_pr_diff", "github_compare",
            "github_create_release",
        ]
        for tname in _github_tools:
            self.capability.register(ToolDefinition(
                name=tname, description=f"GitHub: {tname}",
                handler=_make_skill_handler(tname)))

        # ── External API placeholders ──
        _api_tools = [
            "gitlab_api", "bitbucket_api", "linear_api", "jira_api",
            "notion_api", "datadog_api", "vercel_api", "discord_api",
            "slack_api", "azure_devops_api",
        ]
        for tname in _api_tools:
            def _make_api_handler(name: str):
                def _handler(arg: str) -> str:
                    from app.skills import api_placeholder
                    return api_placeholder(name.replace("_api", ""))[:500]
                return _handler
            self.capability.register(ToolDefinition(
                name=tname, description=f"API: {tname}",
                handler=_make_api_handler(tname)))

        # ── DB-based tools (pre-registered) ──
        if db_session_factory is not None:
            def _make_db_handler(name: str):
                def _handler(arg: str) -> str:
                    db = db_session_factory()
                    try:
                        from app.tools import execute as exec_tool
                        return str(exec_tool(db, name, str(arg).strip()))[:2000]
                    finally:
                        db.close()
                return _handler

            for tname in ("run_command", "read_file", "search_memory",
                          "device_status", "open_app"):
                self.capability.register(ToolDefinition(
                    name=tname, description=f"Tool: {tname}",
                    handler=_make_db_handler(tname)))

            # Catch-all fallback: any unregistered tool → DB
            def _db_fallback(name: str, arg: str) -> str:
                db = db_session_factory()
                try:
                    from app.tools import execute as exec_tool
                    return str(exec_tool(db, name, str(arg).strip()))[:2000]
                finally:
                    db.close()

            self.capability.set_fallback(_db_fallback)

    def reset_session(self, sid: int):
        self._sessions.pop(sid, None)


# Singleton
_runtime: MotherRuntime | None = None


def get_runtime() -> MotherRuntime:
    """Get or create the singleton MotherRuntime."""
    global _runtime
    if _runtime is None:
        from app.db import SessionLocal
        _runtime = MotherRuntime(db_session_factory=SessionLocal)
    return _runtime
