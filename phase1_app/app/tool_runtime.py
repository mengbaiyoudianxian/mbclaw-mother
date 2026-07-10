"""MBclaw Tool Runtime v1.2 — Process-isolated execution layer.

v1.2 changes:
  - run_command uses subprocess.Popen with terminate()→kill()→wait() (no zombie processes)
  - CommandRiskAnalyzer replaces string blacklist with LOW/MEDIUM/HIGH/CRITICAL tiers
  - ToolRegistryEntry v2: category, risk_level, permission, usage_count
  - Non-shell tools (read_file etc.) still use capability.execute via Thread (I/O bound)

Architecture:
  ToolRuntime.execute(name, args)
    → CommandRiskAnalyzer.analyze()
    → Popen (shell) or Thread (capability) with timeout
    → terminate/kill/wait cleanup
    → ToolResult
"""
from __future__ import annotations
import json, os, re, time, logging, traceback, signal
import subprocess, threading
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger("tool_runtime")

# ── data types ────────────────────────────────────────────────


@dataclass
class ToolResult:
    tool_name: str
    status: str           # "success" | "error" | "timeout" | "blocked"
    execution_time: float = 0.0
    stdout: str = ""
    stderr: str = ""
    error: str = ""
    error_type: str = ""  # "timeout" | "permission" | "not_found" | "runtime" | "blocked" | "policy_denied"

    def to_json(self) -> str:
        return json.dumps({
            "tool_name": self.tool_name, "status": self.status,
            "execution_time": round(self.execution_time, 3),
            "stdout": self.stdout[:2000], "stderr": self.stderr[:500],
            "error": self.error[:500], "error_type": self.error_type,
        }, ensure_ascii=False)

    def to_display(self) -> str:
        if self.status == "success":
            return self.stdout[:3000] or "(执行成功，无输出)"
        if self.status == "timeout":
            return f"[超时] {self.tool_name} 执行超时，进程已终止。"
        if self.status == "blocked":
            return f"[已拦截] {self.tool_name}: {self.error}"
        if self.status == "policy_denied":
            return f"[策略拒绝] {self.tool_name}: {self.error}"
        return f"[错误] {self.tool_name}: {self.error or self.stderr or '未知错误'}"


@dataclass
class ToolRegistryEntry:
    """v2: enhanced schema with category, risk_level, permission tracking."""
    name: str
    description: str = ""
    category: str = "general"     # observation | file | shell | memory | device | api
    risk_level: str = "LOW"       # LOW | MEDIUM | HIGH | CRITICAL
    permission: str = "read_only" # read_only | write | admin | disabled
    available: bool = True
    last_check: str = ""
    latency_ms: float = 0.0
    error_count: int = 0
    total_calls: int = 0
    usage_count: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name, "category": self.category,
            "risk_level": self.risk_level, "permission": self.permission,
            "available": self.available, "last_check": self.last_check,
            "latency_ms": self.latency_ms, "usage_count": self.usage_count,
        }


# ── Tool Registry v2 ──────────────────────────────────────────


class ToolRegistry:
    """v2: enhanced tool registry with category/risk/permission tracking."""

    def __init__(self):
        self._tools: dict[str, ToolRegistryEntry] = {}
        self._lock = threading.Lock()

    def register(self, name: str, description: str = "",
                 category: str = "general", risk_level: str = "LOW",
                 permission: str = "read_only") -> ToolRegistryEntry:
        entry = ToolRegistryEntry(name=name, description=description,
                                  category=category, risk_level=risk_level,
                                  permission=permission)
        with self._lock:
            self._tools[name] = entry
        return entry

    def get(self, name: str) -> Optional[ToolRegistryEntry]:
        return self._tools.get(name)

    def list_available(self) -> list[ToolRegistryEntry]:
        return [e for e in self._tools.values() if e.available]

    def list_by_category(self, category: str) -> list[ToolRegistryEntry]:
        return [e for e in self._tools.values() if e.category == category and e.available]

    def mark_call(self, name: str, success: bool, latency_ms: float):
        entry = self._tools.get(name)
        if entry:
            with self._lock:
                entry.total_calls += 1
                entry.usage_count += 1
                entry.last_check = time.strftime("%Y-%m-%d %H:%M:%S")
                entry.latency_ms = latency_ms
                if not success:
                    entry.error_count += 1
                if entry.error_count >= 5:
                    entry.available = False

    def health_summary(self) -> dict:
        tools = {}
        for e in self._tools.values():
            tools[e.name] = e.to_dict()
        return {
            "total": len(self._tools),
            "available_count": sum(1 for e in self._tools.values() if e.available),
            "by_category": {
                cat: len([e for e in self._tools.values()
                         if e.category == cat and e.available])
                for cat in sorted(set(e.category for e in self._tools.values()))
            },
            "tools": tools,
        }

    def format_for_agent(self) -> str:
        """Generate capability declaration from Registry only."""
        available = self.list_available()
        if not available:
            return "当前无可用工具，请联系管理员。"
        lines = ["## 当前可用工具 (来自 Capability Registry)"]
        current_cat = ""
        for e in sorted(available, key=lambda e: (e.category, e.name)):
            if e.category != current_cat:
                current_cat = e.category
                lines.append(f"\n【{current_cat}】")
            risk_mark = {"LOW": "", "MEDIUM": " ⚠️", "HIGH": " 🔒", "CRITICAL": " 🚫"}.get(e.risk_level, "")
            lines.append(f"- {e.name}: {e.description or '(无描述)'}{risk_mark}")
        lines.append(f"\n共 {len(available)} 个工具可用。")
        return "\n".join(lines)


# ── Command Risk Analyzer ─────────────────────────────────────


class CommandRiskAnalyzer:
    """Analyzes shell commands and assigns risk levels.

    LOW:    read-only observation (ls, df, free, ps, cat, echo, uname, hostname)
    MEDIUM: package install, service management (pip, apt, systemctl restart)
    HIGH:   destructive file ops, permission changes (rm, chmod, chown, iptables)
    CRITICAL: system destruction (mkfs, fdisk, wipefs, shutdown, dd)
    """

    RISK_PATTERNS = {
        "LOW": [
            r"^\s*(ls|pwd|df|free|uptime|hostname|uname|whoami|id|date|echo|cat|head|tail|grep|wc|sort|uniq|find|which|whereis|env|printenv|ps|top|netstat|ss|ip\s+addr|ip\s+link|curl|wget)\b",
        ],
        "MEDIUM": [
            r"\b(pip|pip3|npm|yarn|gem|cargo)\s+install\b",
            r"\b(apt|apt-get|yum|dnf|brew)\s+install\b",
            r"\b(systemctl|service)\s+(restart|reload)\b",
            r"\b(docker|podman)\s+(run|start|build)\b",
            r"\b(git\s+clone|git\s+pull)\b",
        ],
        "HIGH": [
            r"\brm\s+-rf?\b", r"\brmdir\b",
            r"\b(chmod|chown|chgrp)\b",
            r"\b(iptables|nft|ufw)\b", r"\buser(add|del|mod)\b",
            r"\bmv\s+.*/(etc|boot|sys|proc|dev)\b",
            r"\bkill\b", r"\bpkill\b", r"\bkillall\b",
            r">\s*/dev/", r"\btee\b",
        ],
        "CRITICAL": [
            r"\b(mkfs|fdisk|wipefs|parted|sfdisk)\b",
            r"\b(shutdown|reboot|halt|poweroff|init\s+[06])\b",
            r"\bdd\s+if=", r"\bformat\b",
            r"\b(:\(\)\s*\{|fork\s*bomb)\b",
            r"\bchmod\s+777\s+/",
        ],
    }

    @classmethod
    def analyze(cls, command: str) -> dict:
        """Analyze a shell command and return risk assessment.

        Returns: {"risk_level": str, "reason": str, "action": "allow"|"deny"|"log"}
        """
        cmd_lower = command.lower().strip()
        if not cmd_lower:
            return {"risk_level": "LOW", "reason": "空命令", "action": "allow"}

        levels = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        for level in levels:
            for pat in cls.RISK_PATTERNS.get(level, []):
                if re.search(pat, cmd_lower):
                    action = "deny" if level == "CRITICAL" else (
                        "log" if level == "HIGH" else "allow")
                    return {
                        "risk_level": level,
                        "reason": f"命令匹配 {level} 风险规则: {pat}",
                        "action": action,
                    }
        # Unknown commands default to MEDIUM risk
        return {"risk_level": "MEDIUM", "reason": "未识别的命令", "action": "log"}


# ── Tool Runtime v1.2 ────────────────────────────────────────


class ToolRuntime:
    """v1.2: Process-isolated tool executor.

    Key changes from v1.1:
      - run_command → subprocess.Popen + terminate(2s)→kill→wait (no zombies)
      - Non-shell tools → capability.execute via Thread (I/O bound, safe)
      - CommandRiskAnalyzer integration for risk-based policy
      - ToolRegistry v2 with category/risk/permission
    """

    DEFAULT_TIMEOUT = 10
    KILL_GRACE = 2  # seconds between SIGTERM and SIGKILL
    LOG_DIR = "logs/tool_runtime"

    def __init__(self, capability=None, registry: ToolRegistry = None):
        self._capability = capability
        self.registry = registry or ToolRegistry()
        self.risk_analyzer = CommandRiskAnalyzer()
        os.makedirs(self.LOG_DIR, exist_ok=True)

    # ── public API ───────────────────────────────────────────

    def execute(self, tool_name: str, arguments: str,
                timeout: int = None) -> ToolResult:
        """Execute tool with process isolation. Never raises."""
        timeout = timeout or self.DEFAULT_TIMEOUT
        t0 = time.time()

        # ── Risk analysis (for shell commands) ──
        risk_info = None
        if tool_name == "run_command":
            risk_info = self.risk_analyzer.analyze(arguments)
            if risk_info["action"] == "deny":
                result = ToolResult(tool_name=tool_name, status="blocked",
                                    error=f"{risk_info['reason']}", error_type="blocked",
                                    execution_time=time.time() - t0)
                self._log(result, arguments, risk_info)
                self.registry.mark_call(tool_name, False, 0)
                return result

        # ── Dispatch: shell → Popen, others → capability ──
        if tool_name == "run_command":
            result = self._execute_shell(arguments, timeout, t0, risk_info)
        else:
            result = self._execute_capability(tool_name, arguments, timeout, t0)

        elapsed_ms = (time.time() - t0) * 1000
        self.registry.mark_call(tool_name, result.status == "success", elapsed_ms)
        self._log(result, arguments, risk_info)
        return result

    def _execute_shell(self, command: str, timeout: int, t0: float,
                       risk: Optional[dict] = None) -> ToolResult:
        """Execute shell command via subprocess.Popen with cleanup."""
        try:
            proc = subprocess.Popen(
                command, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, preexec_fn=os.setsid,
            )
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
                rc = proc.returncode
                elapsed = time.time() - t0
                if rc == 0:
                    return ToolResult(tool_name="run_command", status="success",
                                      stdout=stdout, stderr=stderr,
                                      execution_time=elapsed)
                else:
                    return ToolResult(tool_name="run_command", status="error",
                                      stdout=stdout, stderr=stderr,
                                      error=f"退出码: {rc}", error_type="runtime",
                                      execution_time=elapsed)
            except subprocess.TimeoutExpired:
                # ── Cleanup: terminate → kill → wait ──
                return self._kill_process(proc, command, timeout, t0)
        except FileNotFoundError:
            return ToolResult(tool_name="run_command", status="error",
                              error="命令或shell不可用", error_type="not_found",
                              execution_time=time.time() - t0)
        except Exception as e:
            return ToolResult(tool_name="run_command", status="error",
                              error=str(e)[:500], error_type="runtime",
                              execution_time=time.time() - t0)

    def _kill_process(self, proc: subprocess.Popen, command: str,
                      timeout: int, t0: float) -> ToolResult:
        """Graceful kill: SIGTERM → wait → SIGKILL → wait."""
        try:
            # SIGTERM the process group
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            try:
                proc.wait(timeout=self.KILL_GRACE)
            except subprocess.TimeoutExpired:
                # Force kill
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                proc.wait(timeout=2)
        except (ProcessLookupError, OSError):
            pass  # Already dead
        except Exception:
            # Last resort
            try:
                proc.kill()
                proc.wait(timeout=2)
            except Exception:
                pass

        elapsed = time.time() - t0
        # Verify no zombie — read any remaining output
        try:
            leftover_stdout, leftover_stderr = proc.stdout.read(), proc.stderr.read()
        except Exception:
            leftover_stdout, leftover_stderr = "", ""

        return ToolResult(tool_name="run_command", status="timeout",
                          stdout=leftover_stdout[:2000],
                          stderr=leftover_stderr[:500],
                          error=f"命令执行超过 {timeout} 秒，进程已终止 (SIGTERM→SIGKILL)",
                          error_type="timeout",
                          execution_time=elapsed)

    def _execute_capability(self, tool_name: str, arguments: str,
                            timeout: int, t0: float) -> ToolResult:
        """Execute non-shell tool via Capability (Thread-based, I/O safe)."""
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
            return ToolResult(
                tool_name=tool_name, status="timeout",
                error=f"工具执行超时 ({timeout}s)", error_type="timeout",
                execution_time=time.time() - t0)
        if exc_info:
            etype, evalue, tb = exc_info
            return ToolResult(
                tool_name=tool_name, status="error",
                error=str(evalue)[:500],
                error_type=self._classify_error(etype, evalue),
                stderr=tb[:500] if tb else "",
                execution_time=time.time() - t0)
        return result or ToolResult(tool_name=tool_name, status="error",
                                     error="工具返回空结果", error_type="runtime",
                                     execution_time=time.time() - t0)

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
            self.registry.register(name, f"健康检查通过", category="shell" if name == "run_command" else "file")

        # File system test
        fs_ok = True
        test_path = "/tmp/mbclaw_tool_health_test"
        try:
            with open(test_path, "w") as f: f.write("health")
            with open(test_path) as f:
                if f.read() != "health": fs_ok = False
            os.remove(test_path)
        except Exception as e:
            fs_ok = False
            results["filesystem"] = {"status": "error", "error": str(e)[:200]}
        if fs_ok:
            results["filesystem"] = {"status": "success", "latency_ms": 0}

        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.2",
            "tools": results,
            "registry": self.registry.health_summary(),
        }

    def system_info(self) -> ToolResult:
        cmd = ("echo '=== 系统信息 ===' && uname -a && echo && "
               "echo '=== 发行版 ===' && cat /etc/os-release 2>/dev/null | head -5 && echo && "
               "echo '=== 主机名 ===' && hostname && echo && "
               "echo '=== CPU ===' && lscpu 2>/dev/null | head -10 && echo && "
               "echo '=== 内存 ===' && free -h && echo && "
               "echo '=== 磁盘 ===' && df -h / /tmp 2>/dev/null && echo && "
               "echo '=== 进程 Top5 ===' && ps aux --sort=-%cpu | head -6")
        return self.execute("run_command", cmd, timeout=15)

    # ── internals ─────────────────────────────────────────────

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
        if tool_name == "run_command":
            r = subprocess.run(args, shell=True, capture_output=True,
                             text=True, timeout=self.DEFAULT_TIMEOUT)
            return r.stdout or r.stderr or "(无输出)"
        return f"工具不可用: {tool_name} (未接入Capability)"

    def _log(self, result: ToolResult, arguments: str,
             risk: Optional[dict] = None):
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
            if risk:
                record["risk"] = risk
            logfile = os.path.join(self.LOG_DIR, f"tool_{time.strftime('%Y%m%d')}.jsonl")
            with open(logfile, "a") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass
