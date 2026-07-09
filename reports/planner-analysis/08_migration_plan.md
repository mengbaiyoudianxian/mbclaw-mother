# 任务八：Planner 迁移计划

> 注意: Planner 从零开始。当前无任何规划基础设施。

---

## Phase 1 — 从 LLM 提取 TodoWrite（1 天）

### 目标
让 LLM 在需要多步操作时输出结构化 TodoWrite，而不是自由文本。

### 新增
```
planner/__init__.py
planner/planner.py              ← Planner 主类 (Phase 1 最小实现)
planner/state.py                ← TaskState + StepState
```

### 修改
```
mother_runtime.py SYSTEM_PROMPT: 增加 TodoWrite 格式指令
runtime/loop.py: 解析 LLM 输出的 TodoWrite 结构
```

### Prompt 示例
```
当需要多步操作时，先输出 TodoWrite:
{
  "todos": [
    {"content": "...", "status": "in_progress"},
    {"content": "...", "status": "pending"}
  ]
}
然后逐步执行，每完成一步更新 status。
```

### Phase 1 完成标准
- LLM 能在多步任务时输出 TodoWrite
- Planner 能解析 TodoWrite → TaskGraph
- 单步操作行为不变

---

## Phase 2 — Goal Analyzer（1 天）

### 目标
自动判断用户消息是否需要规划。

### 新增
```
planner/goal.py                 ← GoalAnalyzer
```

### 修改
```
runtime/runtime.py: 插入 Planner 调用点
  每个消息进来 → GoalAnalyzer.analyze(message, context) → Goal
    ├── conversation → 跳过 Planner
    ├── simple → 跳过 Planner (直接 Runtime)
    └── multi_step → Planner.plan()
```

### Phase 2 完成标准
- 对话/闲聊不触发 Planner
- 单步操作不触发 Planner
- 多步任务触发 Planner

---

## Phase 3 — Task Graph + Dependency（1.5 天）

### 目标
管理步骤依赖和拓扑排序。

### 新增
```
planner/task_graph.py           ← TaskGraph (DAG)
planner/dependency.py           ← DependencyAnalyzer
```

### 修改
```
planner/planner.py: plan() 调用 split → dependency → sort → queue
```

### Phase 3 完成标准
- Step 依赖关系正确建立
- 拓扑排序正确
- 多 Step 按序执行

---

## Phase 4 — Execution Queue（0.5 天）

### 目标
FIFO 任务队列 + 状态追踪。

### 新增
```
planner/queue.py                ← ExecutionQueue
```

### Phase 4 完成标准
- Step 逐个出队
- 状态实时更新 (pending/running/done/failed)
- 进度可见 (2/5 steps completed)

---

## Phase 5 — Replan（1 天）

### 目标
失败后自动重新规划。

### 新增
```
planner/replan.py               ← Replanner
planner/retry.py                ← RetryPolicy
```

### Phase 5 完成标准
- Step 失败 → Replanner 分析原因
- 可修复 → 插入修复 Step，继续执行
- 不可修复 → 终止，通知用户
- 非关键 Step → 跳过，继续

---

## Phase 6 — Workflow 模板 + Runtime 接入（1 天）

### 目标
预定义常见工作流，全面接入 Runtime。

### 新增
```
planner/workflow.py             ← WorkflowTemplate
```

### 修改
```
runtime/runtime.py: 全面接入 Planner (代替直接调 Worker)
```

### Phase 6 完成标准
- 常见任务匹配模板 (install/update/debug/git)
- Runtime 所有操作经过 Planner
- 可选: 用户可自定义 Workflow

---

## 工作量汇总

| Phase | 内容 | 天数 | 依赖 |
|-------|------|------|------|
| Phase 1 | TodoWrite 提取 | 1 天 | 无 |
| Phase 2 | Goal Analyzer | 1 天 | Phase 1 |
| Phase 3 | Task Graph + Dependency | 1.5 天 | Phase 2 |
| Phase 4 | Execution Queue | 0.5 天 | Phase 3 |
| Phase 5 | Replan | 1 天 | Phase 4 |
| Phase 6 | Workflow + Runtime 接入 | 1 天 | Phase 5 + Runtime |
| **总计** | | **6 天** | |

## 影响范围

| 文件 | Phase 1 | Phase 2 | Phase 3-6 |
|------|---------|---------|-----------|
| mother_runtime.py | ✏️ 改 Prompt | — | — |
| runtime/loop.py | ✏️ 解析 TodoWrite | — | — |
| runtime/runtime.py | — | ✏️ 插入 Planner | ✏️ 全面接入 |
| planner/ | ✨ 新建 2 文件 | ✨ 新建 1 文件 | ✨ 新建 5 文件 |

## 优先级说明

Planner 是 **P2 优先级**（低于 Runtime/P1, Governor/P1，高于 Scheduler/P3）。

原因：
- 当前单轮对话场景不需要规划
- 多步任务场景在 MBclaw 中占比 < 20%
- 但缺少 Planner 限制了复杂任务能力
