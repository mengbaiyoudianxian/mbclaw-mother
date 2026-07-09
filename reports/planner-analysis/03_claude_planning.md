# 任务三：Claude Code Planning 分析

## Claude Code 规划相关设计

### 属于 Planner 的设计

| 设计 | 位置 | 说明 | 属于 Planner 的理由 |
|------|------|------|-------------------|
| **feature-dev 7-phase** | plugins/feature-dev/ | 结构化开发流程: explore → design → implement → test → review → iterate → complete | 预定义工作流 → Planner 的 Workflow |
| **TodoWrite 工具** | Claude 内置工具 | LLM 输出结构化 TODO: {tasks: [{content, status, activeForm}]} | 任务状态管理 → Planner 的 Task State |
| **ralph-loop 迭代** | plugins/ralph-wiggum/ | 自主迭代: 重复执行直到完成 | 自动重规划 → Planner 的 Replan |
| **code-review 并行** | plugins/code-review/ | 5 个并行 Agent 各自负责一个维度 | SubTask 并行 → Planner 的 Dependency Graph |
| **Long Task Continue** | Claude 原生 | 长任务中断后自动恢复 | Task Resume → Planner 的 Task State |

### 属于 Runtime 的设计

| 设计 | 属于 Runtime 的理由 |
|------|-------------------|
| Checkpoint 保存/恢复 | Governor 管理 |
| Context Compression | Context Engine 管理 |
| Tool 执行 | Worker 管理 |
| Streaming | Scheduler 管理 |

### 核心设计：TodoWrite

```
Claude Code TodoWrite 格式:
{
  "todos": [
    {"content": "读取配置文件", "status": "in_progress", "activeForm": "读取配置"},
    {"content": "修改数据库连接", "status": "pending", "activeForm": "修改连接"},
    {"content": "验证修改结果", "status": "pending", "activeForm": "验证结果"}
  ]
}
```

**MBclaw 应用**: Planner 应从 LLM 输出中解析 TodoWrite 格式的任务列表。

### 核心设计：feature-dev 7-phase

```
explore → design → implement → test → review → iterate → complete
  │         │          │         │       │         │          │
  └─读代码  └─出方案   └─写代码  └─测试  └─审查   └─循环    └─结束
```

**MBclaw 应用**: 预定义 Workflow 模板，Planner 选择匹配的 Workflow。

## 可直接借鉴

| Claude 设计 | MBclaw Planner | 优先级 |
|------------|---------------|--------|
| TodoWrite 格式 | task.py TaskState model | P0 |
| feature-dev 7-phase | workflow.py 预定义模板 | P1 |
| ralph-loop 迭代 | replan.py 自动重规划 | P2 |
| Long Task Resume | task.py resume() | P2 |

## 不能迁移

- Claude API 专有的 thinking/tool_use 交替格式
- SubAgent 系统 (5 个并行 Agent) — MBclaw 单 Agent

## 推荐指数

★★★★☆ — TodoWrite + Workflow 模板是最直接的 Planner 参考
