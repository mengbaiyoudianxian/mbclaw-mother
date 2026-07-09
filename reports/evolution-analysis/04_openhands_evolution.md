# 任务四：OpenHands Evolution

## OpenHands 没有 Evolution Engine

OpenHands 也没有独立的 Evolution 模块。它通过以下间接机制实现"学习"：

### Trajectory（轨迹）

```
每次 Agent 运行 → 完整记录:
  - 每轮 Agent 决策 (think + action)
  - 工具调用结果 (observation)
  - 最终任务结果 (success/failure)
  → 存储为 Trajectory
  → 用于: 调试 + 评估 + 训练 (不是自动学习)
```

### Condenser（压缩）

```
Condenser.condense(history):
  - 压缩对话历史 → 提取关键信息
  - 输出: 摘要 → 放回 Context
  - 不是 Evolution: 不改变系统行为，只优化 Context
```

### Task Result → Metrics

```
Task 完成 → 记录:
  - success_rate
  - avg_turns
  - tool_errors
  → Dashboard 展示
  → 不是自动学习
```

---

## OpenHands Agent 如何从"失败"中学习

```
答案: 不自动学习。

当前 OpenHands:
  - 失败 → 记录 Trajectory (用于人工分析)
  - 失败 → 用户手动改进 Prompt/Rules
  - 失败 → 不会自动调整下次行为

未来可能 (推测):
  - Trajectory → Evaluation → 发现模式
  - 模式 → Prompt 优化建议
  - 但仍在设计中
```

## 属于 Memory 还是 Session 还是 Evolution

| OpenHands 数据 | 归属 | MBclaw |
|---------------|------|--------|
| Trajectory | Session (当前) → Memory (长期) | experiences 表 |
| Task Result | Session → Metrics | KeyMetrics |
| Condenser output | Context (临时) | Context Engine |
| User Settings | Memory | user_profiles (远期) |
| Agent配置 (model/temperature) | Runtime config | Runtime 配置 |

## 推荐指数

★★☆☆☆ — 没有 Evolution Engine，不参考
