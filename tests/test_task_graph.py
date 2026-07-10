"""Tests for MBOS TaskGraph — dependency management, cycle detection, topological sort."""
import pytest
from app.planner.task_graph import Task, TaskGraph, TaskStatus


class TestTask:
    def test_task_creation(self):
        task = Task(id="t1", name="test", type="analysis")
        assert task.id == "t1"
        assert task.name == "test"
        assert task.type == "analysis"
        assert task.status == TaskStatus.PENDING
        assert task.dependency == []

    def test_task_with_dependencies(self):
        task = Task(id="t2", name="dep task", type="action",
                    dependency=["t1"], required_capability="shell")
        assert task.dependency == ["t1"]
        assert task.required_capability == "shell"


class TestTaskGraph:
    def test_simple_graph(self):
        tasks = [
            Task(id="1", name="observe", type="system_observe"),
            Task(id="2", name="analyze", type="analysis", dependency=["1"]),
            Task(id="3", name="report", type="report", dependency=["1", "2"]),
        ]
        graph = TaskGraph(goal="test", tasks=tasks)
        assert graph.goal == "test"
        assert len(graph.tasks) == 3

    def test_topological_order_simple(self):
        tasks = [
            Task(id="2", name="analyze", type="analysis", dependency=["1"]),
            Task(id="1", name="observe", type="system_observe"),
            Task(id="3", name="report", type="report", dependency=["1", "2"]),
        ]
        graph = TaskGraph(goal="test", tasks=tasks)
        ordered = graph.topological_order()
        ids = [t.id for t in ordered]
        # 1 must come before 2 and 3, 2 must come before 3
        assert ids.index("1") < ids.index("2")
        assert ids.index("1") < ids.index("3")
        assert ids.index("2") < ids.index("3")

    def test_topological_order_chain(self):
        tasks = [
            Task(id="4", name="d", type="report", dependency=["3"]),
            Task(id="3", name="c", type="action", dependency=["2"]),
            Task(id="2", name="b", type="analysis", dependency=["1"]),
            Task(id="1", name="a", type="system_observe"),
        ]
        graph = TaskGraph(goal="chain", tasks=tasks)
        ordered = graph.topological_order()
        ids = [t.id for t in ordered]
        assert ids == ["1", "2", "3", "4"]

    def test_cycle_detection_simple(self):
        tasks = [
            Task(id="a", name="A", type="action", dependency=["b"]),
            Task(id="b", name="B", type="action", dependency=["a"]),
        ]
        with pytest.raises(ValueError, match="circular dependency"):
            TaskGraph(goal="cycle", tasks=tasks)

    def test_cycle_detection_three_nodes(self):
        tasks = [
            Task(id="a", name="A", type="action", dependency=["c"]),
            Task(id="b", name="B", type="action", dependency=["a"]),
            Task(id="c", name="C", type="action", dependency=["b"]),
        ]
        with pytest.raises(ValueError, match="circular dependency"):
            TaskGraph(goal="three-cycle", tasks=tasks)

    def test_duplicate_id_detection(self):
        tasks = [
            Task(id="1", name="A", type="action"),
            Task(id="1", name="B", type="analysis"),
        ]
        with pytest.raises(ValueError, match="duplicate"):
            TaskGraph(goal="dup", tasks=tasks)

    def test_unknown_dependency(self):
        tasks = [
            Task(id="1", name="A", type="action", dependency=["nonexistent"]),
        ]
        with pytest.raises(ValueError, match="unknown task"):
            TaskGraph(goal="unknown-dep", tasks=tasks)

    def test_ready_tasks(self):
        tasks = [
            Task(id="1", name="observe", type="system_observe"),
            Task(id="2", name="analyze", type="analysis", dependency=["1"]),
        ]
        graph = TaskGraph(goal="ready", tasks=tasks)
        ready = graph.ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "1"

    def test_ready_tasks_after_completion(self):
        tasks = [
            Task(id="1", name="observe", type="system_observe"),
            Task(id="2", name="analyze", type="analysis", dependency=["1"]),
        ]
        graph = TaskGraph(goal="ready2", tasks=tasks)
        # Mark task 1 as success
        tasks[0].status = TaskStatus.SUCCESS
        ready = graph.ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "2"

    def test_no_cycle_valid_dag(self):
        # A diamond dependency: 1→2, 1→3, 2→4, 3→4
        tasks = [
            Task(id="1", name="start", type="system_observe"),
            Task(id="2", name="left", type="analysis", dependency=["1"]),
            Task(id="3", name="right", type="analysis", dependency=["1"]),
            Task(id="4", name="end", type="report", dependency=["2", "3"]),
        ]
        graph = TaskGraph(goal="diamond", tasks=tasks)
        ordered = graph.topological_order()
        ids = [t.id for t in ordered]
        assert ids[0] == "1"
        assert ids[-1] == "4"
