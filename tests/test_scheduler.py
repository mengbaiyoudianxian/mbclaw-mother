"""Tests for MBOS Scheduler v2 — multi-factor task scheduling."""
import pytest
from app.scheduler import Scheduler, ScheduleResult
from app.worker import WorkerPool, create_llm_worker, create_tool_worker, create_system_worker
from app.token_pool import ResourceManager, ProviderInfo, ModelInfo
from app.planner import Task, TaskGraph


class TestScheduler:
    def setup_method(self):
        self.worker_pool = WorkerPool()
        self.worker_pool.register(create_llm_worker("llm-1"))
        self.worker_pool.register(create_llm_worker("llm-2"))
        self.worker_pool.register(create_tool_worker("tool-1"))
        self.worker_pool.register(create_system_worker("sys-1"))

        self.resource_manager = ResourceManager()
        self.resource_manager.register_provider(ProviderInfo(
            provider="zhipu",
            models=[
                ModelInfo(name="glm-4", context="128K", cost="medium",
                          capabilities=["reasoning", "planning", "chat"]),
            ],
            quota_remaining=500,
        ))
        self.resource_manager.register_provider(ProviderInfo(
            provider="deepseek",
            models=[
                ModelInfo(name="deepseek-chat", context="64K", cost="low",
                          capabilities=["reasoning", "chat"]),
            ],
            quota_remaining=500,
        ))

        self.scheduler = Scheduler(
            worker_pool=self.worker_pool,
            resource_manager=self.resource_manager,
        )

    def test_schedule_reasoning_task(self):
        task = Task(id="task_1", name="分析", type="analysis",
                    required_capability="reasoning")
        result = self.scheduler.schedule_task(task)
        assert result.success
        assert result.task_id == "task_1"
        assert result.worker_id == "llm-1"

    def test_schedule_shell_task(self):
        task = Task(id="task_1", name="执行命令", type="action",
                    required_capability="shell")
        result = self.scheduler.schedule_task(task)
        assert result.success
        assert result.worker_id == "tool-1"

    def test_schedule_monitor_task(self):
        task = Task(id="task_1", name="监控", type="system_observe",
                    required_capability="monitor")
        result = self.scheduler.schedule_task(task)
        assert result.success
        assert result.worker_id == "sys-1"

    def test_schedule_no_matching_worker(self):
        task = Task(id="task_1", name="视觉处理", type="analysis",
                    required_capability="vision")
        result = self.scheduler.schedule_task(task)
        assert not result.success
        assert "no available worker" in result.reason

    def test_schedule_all_workers_busy(self):
        # Occupy all LLM workers
        self.worker_pool.get("llm-1").assign("other-task")
        self.worker_pool.get("llm-2").assign("other-task-2")

        task = Task(id="task_1", name="分析", type="analysis",
                    required_capability="reasoning")
        result = self.scheduler.schedule_task(task)
        assert not result.success

    def test_schedule_graph(self):
        tasks = [
            Task(id="1", name="观察", type="system_observe", required_capability="monitor"),
            Task(id="2", name="分析", type="analysis", required_capability="reasoning", dependency=["1"]),
            Task(id="3", name="报告", type="report", required_capability="reasoning", dependency=["1", "2"]),
        ]
        graph = TaskGraph(goal="server_check", tasks=tasks)
        results = self.scheduler.schedule_graph(graph)
        assert len(results) == 3
        assert all(r.success for r in results)

    def test_scheduling_log(self):
        task = Task(id="t1", name="分析", type="analysis",
                    required_capability="reasoning")
        self.scheduler.schedule_task(task)
        log = self.scheduler.get_scheduling_log()
        assert len(log) == 1
        assert log[0].task_id == "t1"

    def test_schedule_result_has_all_fields(self):
        task = Task(id="t1", name="分析", type="analysis",
                    required_capability="reasoning")
        result = self.scheduler.schedule_task(task)
        assert result.task_id
        assert result.worker_id
        assert result.provider
        assert result.model
        assert isinstance(result.success, bool)
        assert isinstance(result.reason, str)
