"""Tests for EmergencyControl — kill switch, stop, resume."""
import pytest
from app.governor import EmergencyControl, ControlResult
from app.state import GlobalState, get_state


class TestEmergencyControl:
    def setup_method(self):
        GlobalState.reset_instance()
        self.ctrl = EmergencyControl()

    def test_emergency_stop(self):
        result = self.ctrl.emergency_stop("TokenPool quota exhausted")
        assert result.success
        assert result.action == "emergency_stop"
        assert self.ctrl.is_stopped()
        assert get_state().is_emergency_stop()

    def test_resume(self):
        self.ctrl.emergency_stop("test stop")
        result = self.ctrl.resume()
        assert result.success
        assert result.action == "resume"
        assert not self.ctrl.is_stopped()
        assert not get_state().is_emergency_stop()

    def test_stop_reason_preserved(self):
        self.ctrl.emergency_stop("quota exhausted")
        assert self.ctrl.stop_reason == "quota exhausted"
        self.ctrl.resume()
        assert self.ctrl.stop_reason == ""

    def test_stop_count(self):
        assert self.ctrl.stop_count == 0
        self.ctrl.emergency_stop("first")
        assert self.ctrl.stop_count == 1
        self.ctrl.resume()
        assert self.ctrl.stop_count == 1  # still 1, only counts stops
        self.ctrl.emergency_stop("second")
        assert self.ctrl.stop_count == 2

    def test_multiple_stops(self):
        """Multiple emergency stops before resume should work."""
        self.ctrl.emergency_stop("first")
        assert self.ctrl.is_stopped()
        self.ctrl.emergency_stop("second")
        assert self.ctrl.is_stopped()
        assert self.ctrl.stop_count == 2
        self.ctrl.resume()
        assert not self.ctrl.is_stopped()

    def test_control_result_has_state(self):
        result = self.ctrl.emergency_stop("test")
        assert "state_before" in result.__dict__
        assert "state_after" in result.__dict__
        assert result.state_before["emergency_stop"] == False
        assert result.state_after["emergency_stop"] == True

    def test_stop_releases_workers(self):
        from app.worker import WorkerPool, create_llm_worker
        pool = WorkerPool()
        w = create_llm_worker("llm-1")
        w.assign("task-1")
        pool.register(w)

        ctrl = EmergencyControl(worker_pool=pool)
        ctrl.emergency_stop("quota")
        # All workers should be released
        assert len(pool.list_available()) == 1

    def test_initial_state_not_stopped(self):
        assert not self.ctrl.is_stopped()

    def test_is_stopped_after_stop(self):
        self.ctrl.emergency_stop("meltdown")
        assert self.ctrl.is_stopped()
