# 任务六：Planner 目录设计

```
planner/
├── __init__.py          导出 Planner
├── planner.py           主 Planner 类
│   class Planner:
│       plan(message, context) → Plan
│       职责: 统筹所有子模块，输出执行计划
│       流程: goal → split → dependency → priority → queue
│
├── goal.py              目标分析器
│   class GoalAnalyzer:
│       analyze(message, context) → Goal
│       职责: 识别用户意图，判断任务类型
│       输出: Goal {type: simple|multi_step|conversation|ambiguous,
│                   description, complexity: 1-10}
│       来源: 新设计 (当前 LLM 隐式完成)
│
├── task_graph.py        任务图
│   class TaskGraph:
│       nodes: list[Step]
│       edges: list[(Step, Step)]  ← 依赖关系
│       add_step(step)
│       add_dependency(before, after)
│       topological_sort() → [Step]
│       职责: 管理 Step 的依赖 DAG
│       来源: 新设计
│
├── dependency.py         依赖分析器
│   class DependencyAnalyzer:
│       analyze(steps) → TaskGraph
│       职责: 分析 Step 之间的依赖关系
│       规则: 文件依赖、数据依赖、顺序依赖
│       来源: 新设计
│
├── queue.py              执行队列
│   class ExecutionQueue:
│       enqueue(step)
│       dequeue() → Step | None
│       peek() → Step | None
│       is_empty() → bool
│       status() → {pending, running, done, failed}
│       职责: FIFO 任务队列
│       来源: 参考 OpenClaw agent-steering-queue.ts
│
├── retry.py              重试策略
│   class RetryPolicy:
│       should_retry(step, error, attempt) → bool
│       next_delay(attempt) → seconds
│       职责: 决定是否重试、等待多久
│       来源: 新设计
│
├── state.py              任务状态
│   class TaskState(Enum):
│       PENDING, RUNNING, DONE, FAILED, SKIPPED, CANCELLED
│   class StepState:
│       step: Step
│       status: TaskState
│       result: any
│       error: str | None
│       started_at, finished_at: datetime
│       职责: 追踪每个 Step 的状态
│       来源: 参考 Claude Code TodoWrite 格式
│
├── workflow.py           预定义工作流
│   class WorkflowTemplate:
│       name: str
│       steps: list[StepTemplate]
│       职责: 常见任务的预定义步骤模板
│       示例:
│         install_package: [check_version, add_source, update, install, verify]
│         git_workflow: [check_status, add, commit, push, create_pr]
│         debug_issue: [read_log, search_error, find_fix, apply_fix, verify]
│       来源: 参考 Claude Code feature-dev 7-phase
│
└── replan.py             重新规划
    class Replanner:
        replan(failed_step, error, remaining_steps) → Plan
        职责: 失败后重新规划
        策略: insert_before | skip | abort | retry
        来源: 参考 Claude Code ralph-loop 迭代
```

## 各文件职责精简

| 文件 | 职责 | 来源 | 状态 |
|------|------|------|------|
| planner.py | 统筹: goal→split→dep→priority→queue | 新设计 | 新建 |
| goal.py | 意图识别 | 新设计 | 新建 |
| task_graph.py | DAG 管理 | 新设计 | 新建 |
| dependency.py | 依赖分析 | 新设计 | 新建 |
| queue.py | 任务队列 | OpenClaw agent-steering-queue | 新建 |
| retry.py | 重试策略 | 新设计 | 新建 |
| state.py | 任务状态 | Claude TodoWrite | 新建 |
| workflow.py | 预定义模板 | Claude feature-dev | 新建 |
| replan.py | 重新规划 | Claude ralph-loop | 新建 |
