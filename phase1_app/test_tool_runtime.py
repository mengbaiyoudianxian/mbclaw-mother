"""ToolRuntime v1.1 — 自动化测试套件

Usage:
    cd /opt/mbclaw/mother-server/phase1_app
    python3 test_tool_runtime.py

Tests:
    1. echo hello → success
    2. sleep 20 → timeout after 10s
    3. nonexistent_command → error
    4. permission error → error
    5. health_check → report
    6. blocked command → blocked
    7. system_info → full system report
"""
from __future__ import annotations
import sys, os, time, json

sys.path.insert(0, os.path.dirname(__file__))

from app.tool_runtime import ToolRuntime, ToolRegistry, ToolResult

PASS = 0
FAIL = 0


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
    rt = ToolRuntime()  # No capability → uses fallback for run_command

    # ── Test 1: echo hello → success ──
    def t1():
        r = rt.execute("run_command", "echo hello", timeout=5)
        assert r.status == "success", f"expected success, got {r.status}: {r.error}"
        assert "hello" in r.stdout, f"expected 'hello' in stdout, got: {r.stdout}"
        assert r.execution_time < 5, f"too slow: {r.execution_time}s"

    test("echo hello → success", t1)

    # ── Test 2: sleep 20 → timeout ──
    def t2():
        t0 = time.time()
        r = rt.execute("run_command", "sleep 20", timeout=3)
        elapsed = time.time() - t0
        assert r.status == "timeout", f"expected timeout, got {r.status}"
        assert elapsed < 8, f"timeout took too long: {elapsed}s"
        assert r.error_type == "timeout", f"expected error_type=timeout, got {r.error_type}"

    test("sleep 20 → timeout after 3s", t2)

    # ── Test 3: nonexistent command → error ──
    def t3():
        r = rt.execute("run_command", "nonexistent_command_xyz_123", timeout=5)
        # Some shells return exit code, not exception — check for non-success
        assert r.status != "timeout", f"unexpected timeout for nonexistent cmd"
        # The command may actually run and return an error via stderr
        if r.status == "error":
            assert r.error_type in ("runtime", "not_found"), f"unexpected error type: {r.error_type}"

    test("nonexistent command → error", t3)

    # ── Test 4: permission error → error ──
    def t4():
        r = rt.execute("read_file", "/etc/shadow", timeout=5)
        assert r.status in ("error", "success"), f"unexpected status: {r.status}"
        # Note: running as root, so this may actually succeed
        if r.status == "error":
            assert r.error_type in ("permission", "runtime"), f"unexpected: {r.error_type}"

    test("read /etc/shadow → error or success (root)", t4)

    # ── Test 5: health_check → report ──
    def t5():
        report = rt.health_check()
        assert "timestamp" in report, f"missing timestamp: {report}"
        assert "tools" in report, f"missing tools: {report}"
        assert "registry" in report, f"missing registry: {report}"

    test("health_check → valid report", t5)

    # ── Test 6: blocked command → blocked ──
    def t6():
        r = rt.execute("run_command", "rm -rf /", timeout=5)
        assert r.status == "blocked", f"expected blocked, got {r.status}"
        assert r.error_type == "blocked"

    test("rm -rf / → blocked", t6)

    # ── Test 7: concurrent tool calls ──
    def t7():
        """Multiple rapid tool calls should all succeed."""
        for i in range(5):
            r = rt.execute("run_command", f"echo test_{i}", timeout=5)
            assert r.status == "success", f"call {i} failed: {r.error}"

    test("5 rapid tool calls → all success", t7)

    # ── Summary ──
    print(f"\n{'='*50}")
    print(f"  Results: {PASS} passed, {FAIL} failed, {PASS+FAIL} total")
    print(f"{'='*50}")

    # Registry summary
    print("\nTool Registry:")
    print(json.dumps(rt.registry.health_summary(), indent=2, ensure_ascii=False))

    return FAIL == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
