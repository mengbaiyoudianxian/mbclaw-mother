"""MBclaw Tool Runtime v1.1 — Reliable tool execution layer.

Provides:
  - Timeout-gated execution (default 10s for commands)
  - Structured JSON result format (status, stdout, stderr, error, execution_time)
  - Error classification (timeout, permission, not_found, runtime_error)
  - Tool Registry with health checks
  - Per-invocation logging to logs/tool_runtime/
  - Blocks dangerous commands

Architecture:
  ToolRuntime.execute(name, args) → capability.execute → tools.execute → subprocess
  All paths produce a ToolResult, never an exception.
"""
from __future__ import annotations
import json, os, re, time, logging, traceback, threading
from dataclasses import dataclass, field
from typing import Optional, Callable

log = logging.getLogger("tool_runtime")

# ── blocked commands ──────────────────────────────────────────
BLOCKED_PATTERNS = [
    "rm -rf /", "rm -rf /*", "shutdown", "reboot", "halt",
    ":(){ :|:& };:", "mkfs", "dd if=/dev/zero",
    "> /dev/sda", "chmod 777 /",
]

# ── data types ────────────────────────────────────────────────


@dataclass
class ToolResult:
    tool_name: str
    status: str           # "success" | "error" | "timeout" | "blocked"
    execution_time: float = 0.0
    stdout: str = ""
    stderr: str = ""
    error: str = ""
    error_type: str = ""  # "timeout" | "permission" | "not_found" | "runtime" | "blocked" | ""

    def to_json(self) -> str:
        return json.dumps({
            "tool_name": self.tool_name,
            "status": self.status,
            "execution_time": round(self.execution_time, 3),
            "stdout": self.stdout[:2000],
            "stderr": self.stderr[:500],
            "error": self.error[:500],
            "error_type": self.error_type,
        }, ensure_ascii=False)

    def to_display(self) -> str:
        """Human-readable result for LLM context."""
        if self.status == "success":
            return self.stdout[:3000] or "(执行成功，无输出)"
        if self.status == "timeout":
            return f"[超时] {self.tool_name} 执行超过限制时间，已终止。"
        if self.status == "blocked":
            return f"[已拦截] {self.tool_name}: {self.error}"
        return f"[错误] {self.tool_name}: {self.error or self.stderr or '未知错误'}"


@dataclass
class ToolRegistryEntry:
    name: str
    description: str
    available: bool = True
    permission: str = "root"
    last_check: str = ""
    latency_ms: float = 0.0
    error_count: int = 0
    total_calls: int = 0


# ── Tool Registry ────────────────────────────────────────────


class ToolRegistry:
    """Tracks tool availability, status, and usage stats.

    Agent MUST read this registry before claiming tool support.
    """

    def __init__(self):
        self._tools: dict[str, ToolRegistryEntry] = {}
        self._lock = threading.Lock()

    def register(self, name: str, description: str = "",
                 permission: str = "root") -> ToolRegistryEntry:
        entry = ToolRegistryEntry(name=name, description=description,
                                  permission=permission)
        with self._lock:
            self._tools[name] = entry
        return entry

    def get(self, name: str) -> Optional[ToolRegistryEntry]:
        return self._tools.get(name)

    def list_available(self) -> list[ToolRegistryEntry]:
        return [e for e in self._tools.values() if e.available]

    def mark_call(self, name: str, success: bool, latency_ms: float):
        entry = self._tools.get(name)
        if entry:
            with self._lock:
                entry.total_calls += 1
                entry.last_check = time.strftime("%Y-%m-%d %H:%M:%S")
                entry.latency_ms = latency_ms
                if not success:
                    entry.error_count += 1
                if entry.error_count >= 5:
                    entry.available = False

    def health_summary(self) -> dict:
        tools = {}
        for e in self._tools.values():
            tools[e.name] = {
                "available": e.available,
                "permission": e.permission,
                "last_check": e.last_check,
                "latency_ms": e.latency_ms,
                "calls": e.total_calls,
                "errors": e.error_count,
            }
        return {"total": len(self._tools),
                "available_count": sum(1 for e in self._tools.values() if e.available),
                "tools": tools}

    def format_for_agent(self) -> str:
        """Generate a tool list the agent can use to answer capability questions."""
        available = self.list_available()
        if not available:
            return "当前无可用工具。"
        lines = ["当前可用工具:"]
        for e in available:
            lines.append(f"- {e.name}: {e.description or '(无描述)'}")
        return "\n".join(lines)


# ── Tool Runtime v1.1 ────────────────────────────────────────


class ToolRuntime:
    """Reliable tool executor with timeout, structured output, error recovery.

    Wraps the existing Capability.execute() / tools.execute() with:
      - Per-call timeout (configurable per tool)
      - Structured ToolResult (never returns raw strings)
      - Error classification
      - Blocked command detection
      - JSON logging to logs/tool_runtime/
      - Registry tracking
    """

    DEFAULT_TIMEOUT = 10  # seconds
    LOG_DIR = "logs/tool_runtime"

    def __init__(self, capability=None, registry: ToolRegistry = None):
        self._capability = capability  # Capability instance from kernel
        self.registry = registry or ToolRegistry()
        self._blocked = [re.compile(p, re.IGNORECASE) for p in BLOCKED_PATTERNS]
        os.makedirs(self.LOG_DIR, exist_ok=True)

    # ── public API ───────────────────────────────────────────

    def execute(self, tool_name: str, arguments: str,
                timeout: int = None) -> ToolResult:
        """Execute a tool with full safeguards. Never raises.

        Args:
            tool_name: Name of the tool (e.g. 'run_command', 'read_file').
            arguments: Argument string passed to the tool handler.
            timeout: Per-call timeout override (None = use default).

        Returns:
            ToolResult with structured status, output, and error info.
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        t0 = time.time()

        # ── Blocked check ──
        blocked_reason = self._check_blocked(tool_name, arguments)
        if blocked_reason:
            result = ToolResult(tool_name=tool_name, status="blocked",
                                error=blocked_reason, error_type="blocked",
                                execution_time=time.time() - t0)
            self._log(result, arguments)
            self.registry.mark_call(tool_name, False, (time.time() - t0) * 1000)
            return result

        # ── Execute with timeout ──
        result = None
        exc_info = None

        def _run():
            nonlocal result, exc_info
            try:
                if self._capability is not None:
                    output = self._capability.execute(tool_name, arguments)
                else:
                    output = self._execute_fallback(tool_name, arguments)
                result = ToolResult(
                    tool_name=tool_name, status="success",
                    stdout=str(output), execution_time=time.time() - t0)
            except Exception as e:
                exc_info = (type(e), e, traceback.format_exc())

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            result = ToolResult(
                tool_name=tool_name, status="timeout",
                error=f"命令执行超过 {timeout} 秒", error_type="timeout",
                execution_time=time.time() - t0)
        elif exc_info:
            etype, evalue, tb = exc_info
            error_type = self._classify_error(etype, evalue)
            result = ToolResult(
                tool_name=tool_name, status="error",
                error=str(evalue)[:500], error_type=error_type,
                stderr=tb[:500] if tb else "",
                execution_time=time.time() - t0)

        elapsed_ms = (time.time() - t0) * 1000
        self.registry.mark_call(tool_name, result.status == "success", elapsed_ms)
        self._log(result, arguments)
        return result

    def health_check(self) -> dict:
        """Run startup health checks for core tools. Returns health report."""
        results = {}
        test_tools = [
            ("run_command", "echo TOOL_HEALTH_CHECK"),
            ("read_file", "/etc/hostname"),
        ]
        for name, arg in test_tools:
            t0 = time.time()
            r = self.execute(name, arg, timeout=5)
            results[name] = {
                "status": r.status,
                "latency_ms": round((time.time() - t0) * 1000),
                "error": r.error if r.status != "success" else "",
            }
            self.registry.register(name, f"健康检查通过 ({(time.time()-t0)*1000:.0f}ms)")

        # File system test: write temp file, read, delete
        fs_ok = True
        test_path = "/tmp/mbclaw_tool_health_test"
        try:
            with open(test_path, "w") as f:
                f.write("health")
            with open(test_path) as f:
                if f.read() != "health":
                    fs_ok = False
            os.remove(test_path)
        except Exception as e:
            fs_ok = False
            results["filesystem"] = {"status": "error", "error": str(e)[:200]}
        if fs_ok:
            results["filesystem"] = {"status": "success", "latency_ms": 0}

        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tools": results,
            "registry": self.registry.health_summary(),
        }

    def system_info(self) -> ToolResult:
        """Execute a full system info query (uname, cpu, memory, disk, processes)."""
        cmd = ("echo '=== 系统信息 ===' && uname -a && echo && "
               "echo '=== 发行版 ===' && cat /etc/os-release 2>/dev/null | head -5 && echo && "
               "echo '=== 主机名 ===' && hostname && echo && "
               "echo '=== CPU ===' && lscpu 2>/dev/null | head -10 || cat /proc/cpuinfo 2>/dev/null | head -10 && echo && "
               "echo '=== 内存 ===' && free -h && echo && "
               "echo '=== 磁盘 ===' && df -h / /tmp 2>/dev/null && echo && "
               "echo '=== 进程 Top5 ===' && ps aux --sort=-%cpu | head -6")
        return self.execute("run_command", cmd, timeout=15)

    # ── internals ─────────────────────────────────────────────

    def _check_blocked(self, tool_name: str, args: str) -> str:
        combined = f"{tool_name} {args}"
        for pat in self._blocked:
            if pat.search(combined):
                return f"命令被安全策略拦截: 匹配规则 '{pat.pattern}'"
        return ""

    def _classify_error(self, etype, evalue) -> str:
        msg = str(evalue).lower()
        if "permission denied" in msg or "operation not permitted" in msg:
            return "permission"
        if "not found" in msg or "no such file" in msg:
            return "not_found"
        if "timeout" in msg:
            return "timeout"
        return "runtime"

    def _execute_fallback(self, tool_name: str, args: str) -> str:
        """Fallback when no Capability is wired — direct subprocess for shell commands."""
        if tool_name == "run_command":
            import subprocess
            r = subprocess.run(args, shell=True, capture_output=True,
                             text=True, timeout=self.DEFAULT_TIMEOUT)
            return r.stdout or r.stderr or "(无输出)"
        return f"工具不可用: {tool_name} (未接入Capability)"

    def _log(self, result: ToolResult, arguments: str):
        """Write structured JSON log to logs/tool_runtime/."""
        try:
            record = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": result.tool_name,
                "arguments": arguments[:500],
                "status": result.status,
                "execution_time": round(result.execution_time, 3),
                "stdout": result.stdout[:1000],
                "stderr": result.stderr[:500],
                "error": result.error[:500],
                "error_type": result.error_type,
            }
            logfile = os.path.join(
                self.LOG_DIR,
                f"tool_{time.strftime('%Y%m%d')}.jsonl")
            with open(logfile, "a") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass
