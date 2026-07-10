"""Tests for MBOS Planner — goal decomposition."""
import pytest
from app.planner import Planner, TaskGraph


class TestPlanner:
    def setup_method(self):
        self.planner = Planner()

    def test_empty_goal_raises(self):
        with pytest.raises(ValueError, match="empty"):
            self.planner.create_plan("")

    def test_whitespace_goal_raises(self):
        with pytest.raises(ValueError, match="empty"):
            self.planner.create_plan("   ")

    def test_server_check_decomposition(self):
        graph = self.planner.create_plan("检查服务器状态并生成报告")
        assert isinstance(graph, TaskGraph)
        assert len(graph.tasks) == 3
        task_ids = [t.id for t in graph.tasks]
        assert "task_1" in task_ids
        assert "task_2" in task_ids
        assert "task_3" in task_ids
        # Check dependencies
        t2 = next(t for t in graph.tasks if t.id == "task_2")
        assert "task_1" in t2.dependency

    def test_deploy_decomposition(self):
        graph = self.planner.create_plan("部署新项目到生产环境")
        assert len(graph.tasks) == 4
        assert graph.tasks[0].type == "system_observe"

    def test_code_review_decomposition(self):
        graph = self.planner.create_plan("帮我审查这段代码")
        assert len(graph.tasks) == 3
        types = [t.type for t in graph.tasks]
        assert "system_observe" in types
        assert "analysis" in types
        assert "report" in types

    def test_bug_fix_decomposition(self):
        graph = self.planner.create_plan("修复登录页面的bug")
        assert len(graph.tasks) == 3
        assert graph.tasks[0].type == "analysis"

    def test_generic_goal_fallback(self):
        graph = self.planner.create_plan("随便做点什么")
        assert len(graph.tasks) == 3
        # Should use default pattern
        assert graph.tasks[0].type == "analysis"
        assert graph.tasks[1].type == "action"
        assert graph.tasks[2].type == "system_observe"

    def test_backup_decomposition(self):
        graph = self.planner.create_plan("备份数据库")
        assert len(graph.tasks) == 3

    def test_search_decomposition(self):
        graph = self.planner.create_plan("搜索所有Python文件")
        assert len(graph.tasks) == 3
        assert graph.tasks[1].type == "action"

    def test_plan_summary(self):
        graph = self.planner.create_plan("检查服务器状态并生成报告")
        summary = self.planner.plan_summary(graph)
        assert "Goal:" in summary
        assert "system_observe" in summary
        assert "analysis" in summary
        assert "report" in summary

    def test_all_tasks_have_required_fields(self):
        """Every task must have id, name, type, priority, dependency, required_capability, status."""
        graph = self.planner.create_plan("检查服务器状态并生成报告")
        for task in graph.tasks:
            assert task.id
            assert task.name
            assert task.type
            assert isinstance(task.priority, int)
            assert isinstance(task.dependency, list)
            assert isinstance(task.required_capability, str)
            assert task.status is not None
