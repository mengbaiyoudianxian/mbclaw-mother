# 任务七：Planner 生命周期

## 完整生命周期

```
[1] Receive Goal
    Runtime 收到用户消息
    触发: 每个用户消息
    决策: 是否需要 Planner？
      ├── 单句对话 → 跳过 Planner，直接 Runtime
      ├── 明确单步操作 → 跳过 Planner
      └── 疑似多步任务 → 进入 Planner
    │
    ▼
[2] Analyze Goal
    Goal Analyzer 分析意图
    输入: User Message + Conversation Context
    输出: Goal {type, description, complexity}
    状态: goal_analyzing
    │
    ▼
[3] Split Task
    Task Splitter 分解步骤
    输入: Goal + Context
    输出: [Step, Step, ...]
    来源:
      ├── LLM 推断 (主路径: 让 LLM 输出结构化步骤)
      ├── Workflow 模板匹配 (辅助: 匹配预定义工作流)
      └── 用户显式列表 (用户主动给步骤)
    状态: task_splitting
    可自动重规划: ✅ 是 (LLM 可重新生成)
    │
    ▼
[4] Dependency Build
    Dependency Analyzer 分析依赖
    输入: [Step]
    输出: TaskGraph (DAG)
    规则:
      ├── 文件依赖: Step 2 需要 Step 1 的输出文件
      ├── 数据依赖: Step 2 需要 Step 1 的结果数据
      └── 顺序依赖: Step 2 必须在 Step 1 之后 (常识)
    状态: dependency_building
    可自动重规划: ✅ 是 (重新分析)
    │
    ▼
[5] Priority Sort
    拓扑排序 → 确定执行顺序
    输入: TaskGraph
    输出: ordered [Step]
    算法: Kahn's algorithm (拓扑排序)
    状态: priority_sorting
    可自动重规划: ✅ 是 (重新排序)
    │
    ▼
[6] Send to Scheduler  ← 必须等待 Scheduler
    Step 逐个出队 → Scheduler.execute(step)
    输入: Step
    输出: Observation (by Scheduler/Worker)
    状态: executing
    阻塞点: LLM 调用 + 工具执行
    必须等待 Scheduler: ✅ 是
    │
    ▼
[7] Observe
    收集 Scheduler 执行结果
    输入: Observation
    检查:
      ├── 成功 → [8] 继续下一个 Step
      ├── 失败但可修复 → [9] Replan
      ├── 失败不可修复 → [10] 终止
      └── 用户取消 → [10] 终止
    状态: observing
    必须等待 Scheduler: ✅ 是
    │
    ▼
[8] Next Step / Loop
    如果还有未执行的 Step:
      → 出队下一个 → [6] Send to Scheduler
    否则:
      → [10] Complete
    │
    ▼
[9] Replan
    分析失败原因 → 调整计划
    策略:
      ├── insert: 插入修复步骤(如 "安装缺失的依赖")
      ├── skip: 跳过非关键步骤
      ├── retry: 相同 Step 重试
      └── abort: 无法修复 → [10] 终止
    状态: replanning
    可自动重规划: ✅ 是 (核心能力)
    │
    ▼
[10] Complete
    所有 Step 完成或终止
    汇总结果 → 回复用户
    状态: completed | failed | cancelled
    清理: TaskGraph 归档 (可选)
```

## 可自动重规划 vs 必须等待

| 阶段 | 可自动重规划 | 原因 |
|------|:----------:|------|
| Analyze Goal | ✅ | LLM 可重新分析 |
| Split Task | ✅ | LLM 可重新拆解 |
| Dependency Build | ✅ | 纯算法，可重算 |
| Priority Sort | ✅ | 纯算法，可重排 |
| Send Scheduler | ❌ | 必须等 LLM 返回 |
| Observe | ❌ | 必须等工具执行 |
| Replan | ✅ | 这是重规划本身 |
| Complete | ❌ | 终点 |

## 生命周期状态机

```
           ┌──────────────────────────────────┐
           │                                  │
           ▼                                  │
goal_analyzing → task_splitting → dependency_building
                                     │
                                     ▼
                              priority_sorting
                                     │
                                     ▼
                               ┌─ executing ──→ observing
                               │     │              │
                               │     │         ┌────┴────┐
                               │     │       success   failure
                               │     │         │         │
                               │     │         ▼         ▼
                               │     │      next_step  replanning
                               │     │         │         │
                               │     │         │    ┌────┴────┐
                               │     │         │  insert/skip abort
                               │     │         │    │         │
                               │     │         │    ▼         ▼
                               │     │         │  executing  completed
                               │     │         │             (failed)
                               │     │         │
                               │     │         ▼
                               │     └─── completed
                               │
                               └─── cancelled (用户取消)
```
