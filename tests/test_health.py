"""Tests for HealthChecker — full production health endpoint."""
import pytest
from app.health import HealthChecker, HealthReport
from app.state import GlobalState


class TestHealthChecker:
    def setup_method(self):
        GlobalState.reset_instance()

    def test_quick_health_running(self):
        hc = HealthChecker()
        result = hc.quick_health()
        assert result["status"] == "running"
        assert not result["emergency_stop"]

    def test_quick_health_emergency(self):
        from app.governor import EmergencyControl
        ctrl = EmergencyControl()
        ctrl.emergency_stop("test")

        hc = HealthChecker()
        result = hc.quick_health()
        assert result["status"] == "emergency_stop"
        assert result["emergency_stop"]

        ctrl.resume()

    def test_full_health_without_kernel(self):
        hc = HealthChecker()
        report = hc.full_health()
        assert isinstance(report, HealthReport)
        assert report.status in ("healthy", "degraded")

    def test_full_health_with_kernel(self):
        from app.runtime import MBOSKernel
        from app.memory_bridge import MemoryBridge
        kernel = MBOSKernel()

        hc = HealthChecker(
            kernel=kernel,
            memory_bridge=kernel.memory_bridge,
            token_pool_client=kernel.token_pool,
        )
        report = hc.full_health()

        assert isinstance(report, HealthReport)
        assert report.kernel["status"] == "active"
        assert report.governor["rules"] == 5
        assert report.workers["total"] == 9
        assert report.workers["available"] == 9
        assert not report.emergency_stop

    def test_full_health_during_emergency(self):
        from app.runtime import MBOSKernel
        kernel = MBOSKernel()
        kernel.emergency.emergency_stop("test stop")

        hc = HealthChecker(
            kernel=kernel,
            memory_bridge=kernel.memory_bridge,
            token_pool_client=kernel.token_pool,
        )
        report = hc.full_health()
        assert report.emergency_stop
        assert report.status == "emergency_stop"

        kernel.emergency.resume()

    def test_health_report_fields(self):
        hc = HealthChecker()
        report = hc.full_health()
        assert hasattr(report, "kernel")
        assert hasattr(report, "governor")
        assert hasattr(report, "planner")
        assert hasattr(report, "scheduler")
        assert hasattr(report, "workers")
        assert hasattr(report, "token_pool")
        assert hasattr(report, "memory")
        assert hasattr(report, "tools")
        assert hasattr(report, "emergency_stop")
        assert hasattr(report, "timestamp")

    def test_health_report_tools_status(self):
        hc = HealthChecker()
        report = hc.full_health()
        assert report.tools["status"] == "active"
        assert report.tools["runtime"] == "v1.2"
