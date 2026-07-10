"""Tests for GlobalState — thread-safe singleton store."""
import threading
import pytest
from app.state import GlobalState, StateSnapshot, SystemHealth, TokenStatus, get_state


class TestGlobalState:
    def setup_method(self):
        GlobalState.reset_instance()
        self.state = GlobalState.get_instance()

    def test_singleton(self):
        s1 = GlobalState.get_instance()
        s2 = GlobalState.get_instance()
        assert s1 is s2

    def test_get_set_basic(self):
        self.state.set("current_goal", "检查服务器")
        assert self.state.get("current_goal") == "检查服务器"

    def test_get_nonexistent_default(self):
        assert self.state.get("nonexistent", "default") == "default"

    def test_update_batch(self):
        self.state.update({
            "current_goal": "goal1",
            "active_tasks": ["t1", "t2"],
        })
        assert self.state.get("current_goal") == "goal1"
        assert self.state.get("active_tasks") == ["t1", "t2"]

    def test_is_emergency_stop(self):
        assert not self.state.is_emergency_stop()
        self.state.set("emergency_stop", True)
        assert self.state.is_emergency_stop()

    def test_snapshot(self):
        self.state.set("current_goal", "test_goal")
        self.state.set("active_tasks", ["t1"])
        snap = self.state.snapshot()
        assert isinstance(snap, StateSnapshot)
        assert snap.current_goal == "test_goal"
        assert snap.active_tasks == ["t1"]
        assert not snap.emergency_stop

    def test_snapshot_is_deep_copied(self):
        """Snapshot should be independent of later mutations."""
        self.state.set("current_goal", "original")
        snap = self.state.snapshot()
        self.state.set("current_goal", "changed")
        assert snap.current_goal == "original"
        assert self.state.get("current_goal") == "changed"

    def test_concurrent_access(self):
        """Multiple threads writing/reading should not cause data corruption."""
        errors = []
        state = self.state

        def writer():
            try:
                for i in range(100):
                    state.set("counter", i)
                    state.set("active_tasks", [f"t{i}"])
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(100):
                    snap = state.snapshot()
                    assert isinstance(snap, StateSnapshot)
            except Exception as e:
                errors.append(e)

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrency errors: {errors}"

    def test_reset_instance(self):
        s1 = GlobalState.get_instance()
        s1.set("current_goal", "test")
        GlobalState.reset_instance()
        s2 = GlobalState.get_instance()
        assert s2.get("current_goal") == ""

    def test_get_state_convenience(self):
        s = get_state()
        assert s is GlobalState.get_instance()

    def test_keys(self):
        self.state.set("custom_key", "value")
        assert "custom_key" in self.state.keys

    def test_system_health_dataclass(self):
        h = SystemHealth(status="degraded")
        assert h.status == "degraded"

    def test_token_status_dataclass(self):
        ts = TokenStatus(provider="zhipu", model="glm-4",
                         quota_remaining=100, connected=True)
        assert ts.provider == "zhipu"
        assert ts.connected
