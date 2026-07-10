"""MBOS Kernel v0.1 — 自动化测试套件

Usage:
    cd /opt/mbclaw/mother-server/phase1_app
    python3 test_tool_runtime.py

Tests:
    1. Governor blocks CRITICAL tools
    2. Scheduler creates tasks
    3. TokenPool returns provider status
    4. WorkerPool status changes
    5. Full pipeline: events + audit + execution
    6. Tool timeout → process isolation
    7. CommandRiskAnalyzer → all 4 levels
    8. Dynamic capability prompt
"""
from __future__ import annotations
import sys, os, time, json, subprocess

sys.path.insert(0, os.path.dirname(__file__))

PASS = 0; FAIL = 0


def test(name: str, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  ✅ {name}")
    except AssertionError as e:
        FAIL += 1
        print(f"  ❌ {name}: {e}")
    except Exception as e:
        FAIL += 1
        print(f"  💥 {name}: {e}")


def main():
    # 1. Governor blocks CRITICAL tools
    def t1():
        from app.governor import Governor
        from app.tool_runtime import ToolRegistry
        reg = ToolRegistry()
        reg.register("run_command", "shell", category="shell",
                    risk_level="CRITICAL", permission="admin")
        g = Governor(tool_registry=reg)
        d = g.evaluate("run_command", "rm -rf /")
        assert not d.allow, f"CRITICAL should be denied, got allow={d.allow}"
        assert d.required_action == "deny"

    test("Governor blocks CRITICAL tool", t1)

    # 2. Governor allows LOW risk
    def t2():
        from app.governor import Governor
        from app.tool_runtime import ToolRegistry
        reg = ToolRegistry()
        reg.register("read_file", "file", category="file",
                    risk_level="LOW", permission="read_only")
        g = Governor(tool_registry=reg)
        d = g.evaluate("read_file", "/etc/hostname")
        assert d.allow
        assert d.required_action == "execute"

    test("Governor allows LOW risk", t2)

    # 3. Scheduler creates tasks
    def t3():
        from app.scheduler.scheduler import Scheduler
        s = Scheduler()
        task = s.submit("llm", {"msg": "hello"}, priority=2)
        assert task.status == "pending"
        assert "llm-" in task.task_id
        tasks = s.schedule()
        assert len(tasks) == 1

    test("Scheduler creates + schedules tasks", t3)

    # 4. TokenPool returns provider status
    def t4():
        from app.token_pool.candidate import TokenCandidate
        from app.token_pool.pool import TokenPool
        pool = TokenPool()
        pool.register(TokenCandidate(provider="test", model="test-v1",
                     api_key="sk-test", quota_total=50000, cost_per_1k=0.001))
        status = pool.status()
        assert status["total_candidates"] == 1
        assert len(status["providers"]) == 1
        assert status["providers"][0]["name"] == "test"

    test("TokenPool returns provider status", t4)

    # 5. WorkerPool idle/busy/failed
    def t5():
        from app.workers import WorkerPool, WorkerType, WorkerStatus
        pool = WorkerPool()
        pool.create(WorkerType.TOOL, count=3)
        st = pool.status()
        assert st["total"] == 3
        assert st["idle"] == 3
        w = pool.acquire(WorkerType.TOOL)
        assert w is not None
        st2 = pool.status()
        assert st2["busy"] == 1
        pool.release(w.wid)
        assert pool.status()["idle"] == 3

    test("WorkerPool idle→busy→idle cycle", t5)

    # 6. Tool timeout → process isolation
    def t6():
        from app.tool_runtime import ToolRuntime
        rt = ToolRuntime()
        t0 = time.time()
        r = rt.execute("run_command", "sleep 60", timeout=3)
        elapsed = time.time() - t0
        assert r.status == "timeout", f"got {r.status}"
        assert elapsed < 8
        ps = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        lines = [l for l in ps.stdout.split("\n") if "sleep 60" in l and "grep" not in l]
        assert len(lines) == 0, f"ZOMBIE: {lines}"

    test("sleep 60 → timeout, no zombie", t6)

    # 7. CommandRiskAnalyzer → all 4 levels
    def t7():
        from app.tool_runtime import CommandRiskAnalyzer
        a = CommandRiskAnalyzer.analyze
        assert a("ls -la")["risk_level"] == "LOW"
        assert a("apt install vim")["risk_level"] == "MEDIUM"
        assert a("rm -rf /tmp/test")["risk_level"] == "HIGH"
        assert a("mkfs.ext4 /dev/sda1")["risk_level"] == "CRITICAL"

    test("CommandRiskAnalyzer: all 4 levels", t7)

    # 8. Dynamic capability prompt
    def t8():
        from app.tool_runtime import ToolRegistry
        reg = ToolRegistry()
        reg.register("control_plane", category="observation", risk_level="LOW")
        reg.register("run_command", category="shell", risk_level="HIGH")
        reg.register("read_file", category="file", risk_level="LOW")
        prompt = reg.format_for_agent()
        assert "control_plane" in prompt
        assert "observation" in prompt
        assert "3 个工具可用" in prompt

    test("Registry → dynamic capability prompt", t8)

    print(f"\n{'='*50}")
    print(f"  Results: {PASS} passed, {FAIL} failed, {PASS+FAIL} total")
    print(f"{'='*50}")
    return FAIL == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
