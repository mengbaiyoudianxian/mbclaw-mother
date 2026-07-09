# 任务五：MBclaw Planner 职责设计

> 仅输出职责，不写实现

## Planner 核心定位

Planner = 母体的"任务大脑"，在 Receive 之后、Scheduler 之前。

```
Runtime: Receive → Planner → Scheduler → Worker → Reply

Planner 负责: 用户想做什么？→ 怎么分步做？
Scheduler 负责: 每一步找谁做？(哪个 Provider/Model)
Worker 负责: 每一步具体怎么做？(哪个 Tool)
```

## Planner 流程

```
User Message
    │
    ▼
[Goal Analysis]
    分析用户意图:
    ├── 单步操作？→ 直接返回 1 个 Step
    ├── 多步任务？→ 需要分解
    ├── 对话/闲聊？→ 不需要 Task (直接回复)
    └── 不明确？→ 询问用户澄清
    │
    ▼
[Task Splitting]
    将 Goal 分解为 Step 列表:
    例: "帮我安装 Python3.12" →
      Step 1: 检查当前版本
      Step 2: 添加 PPA 源
      Step 3: apt update
      Step 4: apt install python3.12
      Step 5: 验证安装
    │
    ▼
[Dependency Graph]
    分析 Step 之间的依赖:
      Step 2 依赖 Step 1 (需要知道当前版本)
      Step 4 依赖 Step 3 (需要更新源)
      Step 5 依赖 Step 4 (需要安装完成)
    │
    ▼
[Priority Sort]
    拓扑排序 → 确定执行顺序:
      Step 1 → Step 2 → Step 3 → Step 4 → Step 5
    │
    ▼
[Execution Queue]
    将排好序的 Step 推入队列
    │
    ▼
→ Scheduler (逐个取出执行)
    │
    ▼
[Observation]
    每个 Step 执行后收集结果
    │
    ├── 成功 → 继续下一个 Step
    │
    └── 失败 →
        [Replan]
        分析失败原因:
        ├── 可修复 (缺少依赖) → 插入新的 Step(s) 并重新规划
        ├── 可跳过 (非关键步骤) → 跳过，继续
        └── 致命错误 → 终止，通知用户
    │
    ▼
[Completion]
    所有 Step 完成 → 汇总结果 → 回复用户
```

## 各组件职责

| 组件 | 职责 | 输入 | 输出 |
|------|------|------|------|
| Goal Analysis | 意图识别 | User Message + Context | Goal {type, description, complexity} |
| Task Splitting | 步骤分解 | Goal | [Step, Step, ...] |
| Dependency Graph | 依赖分析 | [Step] | DAG (有向无环图) |
| Priority | 优先级排序 | DAG | 拓扑排序后的 [Step] |
| Queue | 执行队列 | [Step] | 逐个出队的 Step |
| Replan | 重新规划 | Failed Step + Error | 新的 [Step] 或 abort |

## Goal 类型

| 类型 | 说明 | 示例 |
|------|------|------|
| simple | 单步操作 | "读一下 /tmp/log" |
| multi-step | 多步任务 | "安装 Python 3.12" |
| conversation | 对话 | "你好，你是谁？" |
| ambiguous | 不明确 | "帮我处理一下" (需要追问) |
