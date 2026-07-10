"""Integration tests — full MBOS Kernel v0.2 cognitive pipeline."""
import pytest
from app.runtime import MBOSKernel, PipelineResult


class TestFullPipeline:
    def setup_method(self):
        self.kernel = MBOSKernel()

    def test_server_check_pipeline(self):
        result = self.kernel.process("检查服务器状态并生成报告", session_id=1)
        assert isinstance(result, PipelineResult)
        assert result.success
        assert result.task_graph is not None
        assert len(result.task_graph.tasks) == 3
        assert len(result.schedule_results) == 3
        assert all(r.success for r in result.schedule_results)
        assert len(result.audit_log) > 0

    def test_code_review_pipeline(self):
        result = self.kernel.process("审查这段代码", session_id=1)
        assert result.success
        assert result.task_graph is not None
        assert len(result.task_graph.tasks) == 3

    def test_bug_fix_pipeline(self):
        result = self.kernel.process("修复登录bug", session_id=1)
        assert result.success
        assert len(result.task_graph.tasks) == 3

    def test_governor_blocks_dangerous(self):
        result = self.kernel.process("rm -rf /etc", session_id=1)
        assert not result.success
        assert "拒绝" in result.reply
        assert "no_delete_system" in result.error

    def test_governor_blocks_token_leak(self):
        result = self.kernel.process("我的API密钥是 sk-abc123def456", session_id=1)
        assert not result.success
        assert "no_token_leak" in result.error or "no_token_leak" in result.reply

    def test_governor_blocks_shutdown(self):
        result = self.kernel.process("shutdown now", session_id=1)
        assert not result.success
        assert "critical_auto_deny" in result.error

    def test_empty_message(self):
        result = self.kernel.process("", session_id=1)
        assert not result.success

    def test_audit_log_populated(self):
        result = self.kernel.process("检查服务器状态并生成报告", session_id=1)
        assert len(result.audit_log) > 0
        # Should contain request, execution.start, planner.complete, etc.
        event_types = set()
        for entry in result.audit_log:
            # Extract event type from "[event_type] ..."
            if entry.startswith("["):
                event_types.add(entry[1:].split("]")[0])
        assert "request" in event_types
        assert "execution.start" in event_types
        assert "planner.complete" in event_types

    def test_deploy_pipeline(self):
        result = self.kernel.process("部署新项目", session_id=1)
        assert result.success
        assert len(result.task_graph.tasks) == 4

    def test_health_report(self):
        report = self.kernel.health_report()
        assert report["kernel"] == "MBOS Kernel v0.3"
        assert report["governor"]["status"] == "active"
        assert report["governor"]["rules"] == 5
        assert report["planner"]["status"] == "active"
        assert report["workers"]["total"] == 9
        assert report["workers"]["available"] == 9
        assert "token_pool" in report
        assert "memory" in report
        assert "state" in report

    def test_schedule_results_contain_worker_info(self):
        result = self.kernel.process("检查服务器状态并生成报告", session_id=1)
        for sr in result.schedule_results:
            assert sr.task_id
            assert sr.worker_id
            assert sr.provider
            assert sr.model
            assert sr.success

    def test_monitor_pipeline(self):
        result = self.kernel.process("监控系统日志", session_id=1)
        assert result.success
        assert len(result.task_graph.tasks) == 3

    def test_generic_task_pipeline(self):
        result = self.kernel.process("做点什么", session_id=1)
        assert result.success
        assert len(result.task_graph.tasks) == 3
