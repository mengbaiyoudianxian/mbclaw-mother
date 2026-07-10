"""MBOS Planner — task types for cognitive decomposition.

Task and TaskGraph represent decomposed goals with dependency management.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class Task:
    """A single decomposable unit of work.

    Attributes:
        id: Unique task identifier.
        name: Human-readable task name.
        type: Task category (system_observe, analysis, report, action, etc.).
        priority: Execution priority (lower = higher priority).
        dependency: IDs of tasks that must complete before this one.
        required_capability: Capability needed to execute (e.g. 'shell', 'reasoning').
        status: Current execution status.
    """
    id: str
    name: str
    type: str
    priority: int = 0
    dependency: list[str] = field(default_factory=list)
    required_capability: str = ""
    status: TaskStatus = TaskStatus.PENDING


@dataclass
class TaskGraph:
    """A goal decomposed into a directed acyclic graph of Tasks.

    Attributes:
        goal: Original user goal description.
        tasks: Ordered list of Tasks forming the execution plan.
    """
    goal: str
    tasks: list[Task] = field(default_factory=list)

    def __post_init__(self):
        self._validate()

    def _validate(self) -> None:
        """Validate graph integrity — must be a DAG."""
        ids = {t.id for t in self.tasks}
        if len(ids) != len(self.tasks):
            raise ValueError("TaskGraph: duplicate task IDs detected")

        for task in self.tasks:
            for dep in task.dependency:
                if dep not in ids:
                    raise ValueError(
                        f"TaskGraph: task '{task.id}' depends on unknown task '{dep}'"
                    )

        cycle = self._detect_cycle()
        if cycle:
            raise ValueError(
                f"TaskGraph: circular dependency detected: {' → '.join(cycle)}"
            )

    def _detect_cycle(self) -> Optional[list[str]]:
        """Detect and return a cycle path if one exists, using DFS."""
        id_to_task = {t.id: t for t in self.tasks}
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {t.id: WHITE for t in self.tasks}
        parent: dict[str, Optional[str]] = {t.id: None for t in self.tasks}

        def dfs(node_id: str) -> Optional[list[str]]:
            color[node_id] = GRAY
            for dep in id_to_task[node_id].dependency:
                if color[dep] == GRAY:
                    path = [dep, node_id]
                    cur = node_id
                    while parent.get(cur) and parent[cur] != dep:
                        cur = parent[cur]
                        path.append(cur)
                    path.append(dep)
                    return path
                if color[dep] == WHITE:
                    parent[dep] = node_id
                    result = dfs(dep)
                    if result:
                        return result
            color[node_id] = BLACK
            return None

        for task in self.tasks:
            if color[task.id] == WHITE:
                result = dfs(task.id)
                if result:
                    return result
        return None

    def topological_order(self) -> list[Task]:
        """Return tasks in topological (Kahn's) order.

        Returns:
            Tasks sorted so that dependencies precede dependents.
        """
        in_degree: dict[str, int] = {t.id: 0 for t in self.tasks}
        adj: dict[str, list[str]] = {t.id: [] for t in self.tasks}

        for task in self.tasks:
            for dep in task.dependency:
                adj[dep].append(task.id)
                in_degree[task.id] += 1

        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        result: list[Task] = []
        id_to_task = {t.id: t for t in self.tasks}

        while queue:
            tid = queue.pop(0)
            result.append(id_to_task[tid])
            for neighbor in adj[tid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self.tasks):
            raise RuntimeError(
                "TaskGraph: topological sort failed — cycle may exist despite validation"
            )
        return result

    def ready_tasks(self) -> list[Task]:
        """Return tasks whose dependencies are all satisfied and status is PENDING."""
        completed = {t.id for t in self.tasks if t.status == TaskStatus.SUCCESS}
        return [
            t for t in self.tasks
            if t.status == TaskStatus.PENDING
            and all(d in completed for d in t.dependency)
        ]
