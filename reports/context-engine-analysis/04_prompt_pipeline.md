# 任务四：Prompt Pipeline 结构设计

> 不写 Prompt 文本，只分析结构

---

## 最终 Prompt 分层结构

```
┌─────────────────────────────────────────────┐
│ Layer 1: System Identity          (固定)    │
│   - 角色定义: "你是母体-小梦"                │
│   - 基本行为规则                             │
│   - 来源: context/templates/identity.yml    │
├─────────────────────────────────────────────┤
│ Layer 2: Governor Constraints     (固定)    │
│   - 禁止操作列表 (HARD_DENY)                 │
│   - 权限提示                                 │
│   - 来源: Governor.policy 动态注入           │
├─────────────────────────────────────────────┤
│ Layer 3: Memory Recall            (动态)    │
│   - 相关记忆片段: "相关记忆：..."             │
│   - 来源: Memory.query() → ContextEngine     │
│   - Token 分配: 15% of budget               │
├─────────────────────────────────────────────┤
│ Layer 4: Planner Context          (可选)    │
│   - 当前 Task 状态: "当前任务步骤 2/5"       │
│   - 待执行 Step 列表                         │
│   - 来源: Planner 动态注入                   │
│   - Token 分配: 10% of budget               │
├─────────────────────────────────────────────┤
│ Layer 5: Capability Registry      (固定)    │
│   - 可用工具列表 (JSON Schema)               │
│   - 来源: CapabilityRegistry.list()         │
│   - Token 分配: 25% of budget               │
├─────────────────────────────────────────────┤
│ Layer 6: Conversation History     (动态)    │
│   - 压缩后或完整对话历史                      │
│   - 来源: Session.history                    │
│   - Token 分配: 40% of budget               │
├─────────────────────────────────────────────┤
│ Layer 7: Active Context           (动态)    │
│   - 工具执行结果 (最新 1-2 轮)               │
│   - 当前错误信息                              │
│   - 来源: Runtime 注入                       │
│   - Token 分配: 5% of budget                │
├─────────────────────────────────────────────┤
│ Layer 8: User Input               (动态)    │
│   - 当前用户消息                              │
│   - 来源: Runtime 传入                       │
│   - Token 分配: 5% of budget                │
└─────────────────────────────────────────────┘
```

---

## Token Budget 分配

```
假设 budget = 6000 tokens (可配置):

Layer 1: System Identity     →  300 tokens (5%)
Layer 2: Governor Constraints →  300 tokens (5%)
Layer 3: Memory Recall       →  900 tokens (15%)
Layer 4: Planner Context     →  600 tokens (10%)
Layer 5: Capability Registry → 1500 tokens (25%)
Layer 6: History             → 2400 tokens (40%)  ← 优先保证
Layer 7: Active Context      →  300 tokens (5%)
Layer 8: User Input          →  300 tokens (5%)
                              ─────────────────
                              6600 tokens (含 10% 冗余)
```

---

## ContextEngine 构建流程

```
ContextEngine.build(messages, session, goal=None):
  1. load_layer(N): 从对应来源取数据
  2. truncate(N, budget): 按预算截断
  3. compress_if_needed(Layer 6): 历史超过预算 → 压缩
  4. assemble(): 按层序拼接
  5. return final_messages  (list[dict])
```

## 压缩时的保留策略

```
重要性排序 (Claude Code 思想):
  P0: 用户明确指令 (不可丢弃)
  P1: 关键决策 (方向性选择)
  P2: 工具执行结果摘要 (不是原始输出)
  P3: 错误信息 (当前未解决的)
  P4: 已解决的历史错误
  P5: 低信息量消息 (确认/问候)

压缩:
  保留 P0-P3 → 丢弃 P4-P5 → 生成摘要
```

---

## 与当前 Hardcode 的对比

| 当前 | 目标 |
|------|------|
| 1 个 System Prompt 字符串 | 8 层独立构建 |
| 全部 Token 给 Prompt | 按比例分配 Budget |
| 压缩: 简单文本拼接 | 压缩: 重要性排序 + LLM 摘要 |
| 工具列表硬编码在 Prompt | 工具列表从 CapabilityRegistry 动态注入 |
| Memory 召回作为 system message | Memory 作为独立 Layer 3 |
