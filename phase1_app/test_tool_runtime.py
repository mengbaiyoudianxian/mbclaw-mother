"""ToolRuntime v1.2 — 自动化测试套件

Usage:
    cd /opt/mbclaw/mother-server/phase1_app
    python3 test_tool_runtime.py

Tests:
    1. echo hello → success
    2. sleep 60 → timeout after 3s, verify no zombie
    3. CRITICAL command → blocked by risk analyzer
    4. HIGH risk command → policy check
    5. control_plane call → valid JSON
    6. health_check → valid report with v1.2
    7. 5 rapid calls → all success
    8. Registry → dynamic capability generation
"""
from __future__ import annotations
import sys, os, time, json, subprocess

sys.path.insert(0, os.path.dirname(__file__))

from app.tool_runtime import ToolRuntime, ToolRegistry, CommandRiskAnalyzer

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
    rt = ToolRuntime()

    # 1. echo hello → success
    def t1():
        r = rt.execute("run_command", "echo hello", timeout=5)
        assert r.status == "success", f"got {r.status}: {r.error}"
        assert "hello" in r.stdout

    test("echo hello → success", t1)

    # 2. sleep 60 → timeout, verify no zombie
    def t2():
        t0 = time.time()
        r = rt.execute("run_command", "sleep 60", timeout=3)
        elapsed = time.time() - t0
        assert r.status == "timeout", f"expected timeout, got {r.status}"
        assert elapsed < 8, f"timeout took too long: {elapsed:.1f}s"
        # Verify no zombie sleep processes
        ps = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        sleep_lines = [l for l in ps.stdout.split("\n") if "sleep 60" in l and "grep" not in l]
        assert len(sleep_lines) == 0, f"ZOMBIE DETECTED: {sleep_lines}"

    test("sleep 60 → timeout, no zombie", t2)

    # 3. CRITICAL command → blocked
    def t3():
        r = rt.execute("run_command", "mkfs.ext4 /dev/sda1", timeout=5)
        assert r.status == "blocked", f"expected blocked, got {r.status}"

    test("mkfs → blocked (CRITICAL)", t3)

    # 4. Risk analyzer
    def t4():
        a = CommandRiskAnalyzer.analyze
        assert a("ls -la")["risk_level"] == "LOW"
        assert a("apt install vim")["risk_level"] == "MEDIUM"
        assert a("rm -rf /tmp/test")["risk_level"] == "HIGH"
        assert a("shutdown now")["risk_level"] == "CRITICAL"
        assert a("shutdown now")["action"] == "deny"

    test("CommandRiskAnalyzer: all 4 levels", t4)

    # 5. control_plane → valid JSON
    def t5():
        from app.tools.control_plane import execute as cp_exec
        r = cp_exec("get_system_status")
        data = json.loads(r)
        assert "cpu" in data, f"no cpu in: {data.keys()}"
        assert "memory" in data
        assert "disk" in data

    test("control_plane get_system_status → valid JSON", t5)

    # 6. health_check → v1.2
    def t6():
        report = rt.health_check()
        assert report.get("version") == "1.2", f"version: {report.get('version')}"
        assert "tools" in report

    test("health_check → v1.2", t6)

    # 7. 5 rapid calls
    def t7():
        for i in range(5):
            r = rt.execute("run_command", f"echo test_{i}", timeout=5)
            assert r.status == "success", f"call {i} failed"

    test("5 rapid calls → all success", t7)

    # 8. Registry → dynamic capability
    def t8():
        reg = ToolRegistry()
        reg.register("control_plane", "系统自检", category="observation",
                    risk_level="LOW", permission="read_only")
        reg.register("run_command", "执行Shell命令", category="shell",
                    risk_level="HIGH", permission="admin")
        reg.register("read_file", "读取文件", category="file",
                    risk_level="LOW", permission="read_only")
        prompt = reg.format_for_agent()
        assert "control_plane" in prompt
        assert "run_command" in prompt
        assert "read_file" in prompt
        assert "observation" in prompt
        assert "3 个工具可用" in prompt

    test("Registry → dynamic capability prompt", t8)

    # Summary
    print(f"\n{'='*50}")
    print(f"  Results: {PASS} passed, {FAIL} failed, {PASS+FAIL} total")
    print(f"{'='*50}")
    return FAIL == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
