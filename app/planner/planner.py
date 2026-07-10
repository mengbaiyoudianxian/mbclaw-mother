"""MBOS Planner Engine v0.1 — cognitive goal decomposition.

Planner converts a user goal into a TaskGraph via rule-based strategies.
V0.1: pattern matching with keyword extraction. No LLM dependency.
"""
from __future__ import annotations

import re
from typing import Optional

from .task_graph import Task, TaskGraph, TaskStatus


# ── Decomposition Strategies ──────────────────────────────────

_DECOMPOSITION_PATTERNS: list[tuple[str, str, list[dict]]] = [
    (
        r"检查.*(?:服务器|系统).*状态.*(?:报告|汇报)",
        "server_check",
        [
            {"id": "task_1", "name": "采集系统指标",
             "type": "system_observe", "priority": 1, "capability": "monitor"},
            {"id": "task_2", "name": "分析健康状态",
             "type": "analysis", "priority": 2, "capability": "reasoning",
             "dep": ["task_1"]},
            {"id": "task_3", "name": "生成状态报告",
             "type": "report", "priority": 3, "capability": "reasoning",
             "dep": ["task_1", "task_2"]},
        ],
    ),
    (
        r"部署.*(?:项目|应用|服务)",
        "deploy",
        [
            {"id": "task_1", "name": "验证部署环境",
             "type": "system_observe", "priority": 1, "capability": "shell"},
            {"id": "task_2", "name": "拉取最新代码",
             "type": "action", "priority": 2, "capability": "shell",
             "dep": ["task_1"]},
            {"id": "task_3", "name": "执行部署脚本",
             "type": "action", "priority": 3, "capability": "shell",
             "dep": ["task_2"]},
            {"id": "task_4", "name": "验证服务健康",
             "type": "system_observe", "priority": 4, "capability": "monitor",
             "dep": ["task_3"]},
        ],
    ),
    (
        r"(?:分析|审查).*(?:代码|code)",
        "code_review",
        [
            {"id": "task_1", "name": "读取目标代码",
             "type": "system_observe", "priority": 1, "capability": "filesystem"},
            {"id": "task_2", "name": "代码质量分析",
             "type": "analysis", "priority": 2, "capability": "reasoning",
             "dep": ["task_1"]},
            {"id": "task_3", "name": "生成审查报告",
             "type": "report", "priority": 3, "capability": "reasoning",
             "dep": ["task_2"]},
        ],
    ),
    (
        r"(?:修复|fix|debug).*(?:bug|问题|错误|error)",
        "bug_fix",
        [
            {"id": "task_1", "name": "定位问题根因",
             "type": "analysis", "priority": 1, "capability": "diagnostic"},
            {"id": "task_2", "name": "实施修复方案",
             "type": "action", "priority": 2, "capability": "shell",
             "dep": ["task_1"]},
            {"id": "task_3", "name": "验证修复效果",
             "type": "system_observe", "priority": 3, "capability": "monitor",
             "dep": ["task_2"]},
        ],
    ),
    (
        r"(?:创建|新建).*(?:项目|仓库|repo)",
        "create_project",
        [
            {"id": "task_1", "name": "初始化项目结构",
             "type": "action", "priority": 1, "capability": "filesystem"},
            {"id": "task_2", "name": "配置开发环境",
             "type": "action", "priority": 2, "capability": "shell",
             "dep": ["task_1"]},
            {"id": "task_3", "name": "初始化版本控制",
             "type": "action", "priority": 3, "capability": "shell",
             "dep": ["task_2"]},
        ],
    ),
    (
        r"(?:监控|monitor).*(?:日志|log)",
        "log_monitor",
        [
            {"id": "task_1", "name": "采集日志数据",
             "type": "system_observe", "priority": 1, "capability": "monitor"},
            {"id": "task_2", "name": "异常模式识别",
             "type": "analysis", "priority": 2, "capability": "diagnostic",
             "dep": ["task_1"]},
            {"id": "task_3", "name": "生成告警摘要",
             "type": "report", "priority": 3, "capability": "reasoning",
             "dep": ["task_2"]},
        ],
    ),
    (
        r"(?:备份|backup)",
        "backup",
        [
            {"id": "task_1", "name": "识别备份目标",
             "type": "analysis", "priority": 1, "capability": "filesystem"},
            {"id": "task_2", "name": "执行数据备份",
             "type": "action", "priority": 2, "capability": "shell",
             "dep": ["task_1"]},
            {"id": "task_3", "name": "验证备份完整性",
             "type": "system_observe", "priority": 3, "capability": "monitor",
             "dep": ["task_2"]},
        ],
    ),
    (
        r"(?:搜索|查找|查询|search|find|query).*(?:文件|file|代码|code|日志|log)",
        "search",
        [
            {"id": "task_1", "name": "解析查询条件",
             "type": "analysis", "priority": 1, "capability": "reasoning"},
            {"id": "task_2", "name": "执行搜索",
             "type": "action", "priority": 2, "capability": "filesystem",
             "dep": ["task_1"]},
            {"id": "task_3", "name": "整理搜索结果",
             "type": "report", "priority": 3, "capability": "reasoning",
             "dep": ["task_2"]},
        ],
    ),
    (
        r"(?:更新|升级|update|upgrade).*(?:系统|软件|依赖|包)",
        "update_system",
        [
            {"id": "task_1", "name": "检查当前版本",
             "type": "system_observe", "priority": 1, "capability": "shell"},
            {"id": "task_2", "name": "备份当前配置",
             "type": "action", "priority": 2, "capability": "filesystem",
             "dep": ["task_1"]},
            {"id": "task_3", "name": "执行升级操作",
             "type": "action", "priority": 3, "capability": "shell",
             "dep": ["task_2"]},
            {"id": "task_4", "name": "验证升级结果",
             "type": "system_observe", "priority": 4, "capability": "monitor",
             "dep": ["task_3"]},
        ],
    ),
    (
        r"(?:测试|test).*(?:接口|API|端点|endpoint)",
        "api_test",
        [
            {"id": "task_1", "name": "识别测试端点",
             "type": "analysis", "priority": 1, "capability": "reasoning"},
            {"id": "task_2", "name": "执行接口测试",
             "type": "action", "priority": 2, "capability": "shell",
             "dep": ["task_1"]},
            {"id": "task_3", "name": "生成测试报告",
             "type": "report", "priority": 3, "capability": "reasoning",
             "dep": ["task_2"]},
        ],
    ),
    (
        r"(?:诊断|diagnose|排查).*(?:性能|performance|慢|卡)",
        "performance_diagnosis",
        [
            {"id": "task_1", "name": "采集性能指标",
             "type": "system_observe", "priority": 1, "capability": "monitor"},
            {"id": "task_2", "name": "识别性能瓶颈",
             "type": "analysis", "priority": 2, "capability": "diagnostic",
             "dep": ["task_1"]},
            {"id": "task_3", "name": "提供优化方案",
             "type": "report", "priority": 3, "capability": "reasoning",
             "dep": ["task_2"]},
        ],
    ),
    (
        r"(?:生成|创建|写).*(?:报告|文档|README|readme|doc)",
        "generate_doc",
        [
            {"id": "task_1", "name": "分析目标内容",
             "type": "analysis", "priority": 1, "capability": "reasoning"},
            {"id": "task_2", "name": "结构化文档大纲",
             "type": "analysis", "priority": 2, "capability": "reasoning",
             "dep": ["task_1"]},
            {"id": "task_3", "name": "生成文档内容",
             "type": "report", "priority": 3, "capability": "reasoning",
             "dep": ["task_2"]},
        ],
    ),
]

# ── Default decomposition for unmatched goals ──
_DEFAULT_PATTERN: list[dict] = [
    {"id": "task_1", "name": "分析任务需求",
     "type": "analysis", "priority": 1, "capability": "reasoning"},
    {"id": "task_2", "name": "执行核心操作",
     "type": "action", "priority": 2, "capability": "shell",
     "dep": ["task_1"]},
    {"id": "task_3", "name": "验证执行结果",
     "type": "system_observe", "priority": 3, "capability": "monitor",
     "dep": ["task_2"]},
]


class Planner:
    """V0.1 cognitive planner — pattern-based goal decomposition.

    Converts user goals into TaskGraph with dependency-aware task decomposition.
    Uses regex pattern matching for known goal types, falls back to generic
    decompose-verify pattern for unknown goals.

    Usage:
        planner = Planner()
        graph = planner.create_plan("检查服务器状态并生成报告")
        for task in graph.topological_order():
            print(task.name)
    """

    def create_plan(self, goal: str) -> TaskGraph:
        """Decompose a user goal into a TaskGraph.

        Args:
            goal: User goal text.

        Returns:
            TaskGraph with decomposed tasks and dependencies.

        Raises:
            ValueError: If goal is empty or whitespace-only.
        """
        if not goal or not goal.strip():
            raise ValueError("Planner: goal must not be empty")

        goal_text = goal.strip()

        for pattern, goal_id, task_specs in _DECOMPOSITION_PATTERNS:
            if re.search(pattern, goal_text, re.IGNORECASE):
                return self._build_graph(goal_text, goal_id, task_specs)

        return self._build_graph(goal_text, "generic_task", _DEFAULT_PATTERN)

    def _build_graph(self, goal: str, goal_id: str,
                     task_specs: list[dict]) -> TaskGraph:
        """Build a TaskGraph from task specifications."""
        tasks: list[Task] = []
        for spec in task_specs:
            tasks.append(Task(
                id=spec["id"],
                name=spec["name"],
                type=spec["type"],
                priority=spec.get("priority", 0),
                dependency=spec.get("dep", []),
                required_capability=spec.get("capability", ""),
                status=TaskStatus.PENDING,
            ))
        return TaskGraph(goal=goal, tasks=tasks)

    def plan_summary(self, graph: TaskGraph) -> str:
        """Generate a human-readable summary of a TaskGraph.

        Args:
            graph: The TaskGraph to summarize.

        Returns:
            Multi-line summary of goal and tasks in topological order.
        """
        lines = [f"Goal: {graph.goal}"]
        try:
            ordered = graph.topological_order()
        except RuntimeError:
            ordered = graph.tasks
        for task in ordered:
            deps = f" (depends: {', '.join(task.dependency)})" if task.dependency else ""
            lines.append(
                f"  [{task.type}] {task.name} "
                f"[{task.priority}] → {task.required_capability}{deps}"
            )
        return "\n".join(lines)
