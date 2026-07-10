"""Integration tests for MBOS Kernel v0.3 — Runtime Integration."""
import pytest
from app.state import GlobalState, get_state


class TestV03Integration:
    def setup_method(self):
        GlobalState.reset_instance()
        from app.runtime import MBOSKernel
        self.kernel = MBOSKernel()

    def test_kernel_has_v03_modules(self):
        """Kernel should have all v0.3 components."""
        assert hasattr(self.kernel, 'state')
        assert hasattr(self.kernel, 'token_pool')
        assert hasattr(self.kernel, 'memory_bridge')
        assert hasattr(self.kernel, 'emergency')

    def test_emergency_stop_blocks_pipeline(self):
        """After emergency stop, process() should return failure."""
        # First, normal request should work
        result = self.kernel.process("检查服务器状态", session_id=1)
        assert result.success

        # Activate emergency stop
        self.kernel.emergency.emergency_stop("quota exhausted")

        # Request should be blocked
        result = self.kernel.process("做点事情", session_id=1)
        assert not result.success
        assert "紧急停止" in result.error or "紧急停止" in result.reply

        # Resume
        self.kernel.emergency.resume()

        # Normal operation restored
        result = self.kernel.process("检查服务器状态", session_id=1)
        assert result.success

    def test_memory_bridge_records_events(self):
        """Memory bridge should record pipeline events."""
        store = self.kernel.memory_bridge.memory_store
        initial_size = store.size()

        self.kernel.process("检查服务器状态并生成报告", session_id=1)

        # Memory should have stored entries from pipeline
        assert store.size() > initial_size

    def test_memory_bridge_records_failures(self):
        """Memory should store failure events."""
        store = self.kernel.memory_bridge.memory_store

        self.kernel.process("rm -rf /etc", session_id=1)

        decisions = store.recent_decisions()
        assert len(decisions) >= 1
        assert any("delete_system" in d.rule_hit for d in decisions)

    def test_global_state_tracks_goal(self):
        """Global state should track current goal."""
        self.kernel.process("检查服务器状态", session_id=1)
        snap = self.kernel.state.snapshot()
        # May have been updated during pipeline
        assert isinstance(snap.current_goal, str)

    def test_health_report_v03(self):
        """Health report should include v0.3 fields."""
        report = self.kernel.health_report()
        assert report["kernel"] == "MBOS Kernel v0.3"
        assert "token_pool" in report
        assert "memory" in report
        assert "state" in report
        assert "emergency_stop" in report["governor"]

    def test_token_pool_offline_in_test(self):
        """In test environment, TokenPool should be offline."""
        assert not self.kernel.token_pool.is_connected

    def test_full_recovery_cycle(self):
        """Emergency stop → block → resume → work again."""
        # Normal
        assert self.kernel.process("检查服务器状态", session_id=1).success

        # Emergency
        self.kernel.emergency.emergency_stop("test")
        assert self.kernel.emergency.is_stopped()
        assert not self.kernel.process("做任何事情", session_id=1).success
        assert not self.kernel.process("其他请求", session_id=1).success

        # Governor still blocks dangerous stuff during emergency
        # (checked before emergency stop since emergency comes after governor)
        # Actually emergency is checked after governor, so dangerous commands
        # are blocked by governor first

        # Resume
        self.kernel.emergency.resume()
        assert not self.kernel.emergency.is_stopped()
        assert self.kernel.process("检查服务器状态", session_id=1).success

    def test_memory_store_query_after_pipeline(self):
        """Memory store should be queryable after pipeline runs."""
        self.kernel.process("检查服务器状态并生成报告", session_id=1)
        successes = self.kernel.memory_bridge.memory_store.recent_successes()
        assert len(successes) >= 1

    def test_state_snapshot_during_emergency(self):
        """Global state should reflect emergency status."""
        self.kernel.emergency.emergency_stop("outage")

        snap = self.kernel.state.snapshot()
        assert snap.emergency_stop

        self.kernel.emergency.resume()
        snap = self.kernel.state.snapshot()
        assert not snap.emergency_stop

    def test_multiple_kernels_share_state(self):
        """Multiple kernel instances share GlobalState singleton."""
        from app.runtime import MBOSKernel
        k1 = MBOSKernel()
        k2 = MBOSKernel()

        k1.state.set("custom_test_key", "hello from k1")
        assert k2.state.get("custom_test_key") == "hello from k1"
