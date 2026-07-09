# 任务四：Codex CLI Pipeline 分析

## 适合 Planner 的设计

| Codex CLI 设计 | 说明 | MBclaw Planner 应用 |
|---------------|------|-------------------|
| **Prompt Pipeline (4层)** | System + Rules + History + User → 顺序组装 | Goal Analyzer: 分层分析输入 |
| **Command Pipeline** | 命令从输入 → 审批 → 沙箱 → 执行 → 结果 | Execution Queue: 串行任务队列 |
| **Execution Order** | codex-rs/exec/ 保证执行顺序 | task_graph.py: 依赖顺序 |
| **Task State (session.rs)** | session 状态: idle/running/done | Task state: pending/running/done/failed |

## 适合 Runtime 的设计

| Codex CLI 设计 | 属于 Runtime 的理由 |
|---------------|-------------------|
| 沙箱执行 (bwrap) | 隔离执行 → Compute/Worker |
| 流式解析 | Scheduler |
| CLI 交互循环 | Runtime loop.py |

## Codex CLI 的核心启发

### Prompt Pipeline 四层模型

```
Layer 1: System Prompt    ← 角色定义（固定）
Layer 2: Rules/Config     ← 用户规则（可配置，来自 CLAUDE.md/.codex/config）
Layer 3: Context/History  ← 当前上下文（动态，来自对话历史）
Layer 4: User Message     ← 用户输入（最新）
```

**Planner 对比**:
```
Layer 1: 不变 → Planner 不需要处理
Layer 2: 用户规则 → Goal Analyzer 参考
Layer 3: 上下文 → Planner 需要结合上下文理解意图
Layer 4: 用户输入 → Goal Analyzer 的输入
```

### Execution Order

```
Codex CLI 执行顺序:
  1. 解析用户输入
  2. 检查执行策略 (execpolicy): allow? deny? ask?
  3. 沙箱准备 (bwrap)
  4. 执行命令
  5. 收集结果
  6. 反馈给 LLM

MBclaw Planner 执行顺序:
  1. 分析用户意图 → Goal
  2. 分解为 Step 列表
  3. 构建依赖图
  4. 优先级排序
  5. 推入执行队列
  6. 逐个发送 Scheduler
```

## 可直接参考

| Codex CLI | MBclaw Planner | 原因 |
|-----------|---------------|------|
| Prompt Pipeline 分层 | Goal Analyzer 分层处理 | 清晰的输入分层 |
| Execution Order | Execution Queue 顺序 | 任务队列设计 |
| session.rs 状态 | TaskState | 显式状态管理 |

## 不要

- Rust 实现 (不可用)
- Sandbox 层 (不属于 Planner)

## 推荐指数

★★☆☆☆ — Pipeline 分层思想可参考，但 Rust 实现无法复用
