# 任务五：Context Engine 职责设计

> 核心：Context Engine 只负责当前会话上下文生命周期，不负责长期记忆

---

## Context Engine 核心定位

```
Context Engine = 母体的"上下文编排器"

职责:
  决定取哪些数据进入 Prompt
  决定什么时候压缩
  决定 Token Budget 分配
  决定压缩策略 (保留什么、丢弃什么)

不负责:
  不存储长期记忆 (Memory 负责)
  不执行工具 (Runtime 负责)
  不分解任务 (Planner 负责)
  不权限判断 (Governor 负责)
```

---

## ✅ Context Engine 负责

| 职责 | 说明 |
|------|------|
| **Prompt 构建** | 从各数据源组装最终 Prompt |
| **分层管理** | 8 层独立管理，各自有来源和 Budget |
| **Token Budget** | 按比例分配每层 Token 配额 |
| **Token 估算** | 精确计算当前 Token 使用量 |
| **压缩触发** | 超过阈值 → 自动压缩 |
| **压缩策略** | 重要性评分 → 保留关键信息 → LLM 生成摘要 |
| **压缩执行** | 调 LLM summarise_session() 生成语义摘要 |
| **Context 恢复** | Checkpoint 恢复时重建上下文 |
| **Context 预热** | 会话创建时预加载 Memory + History |
| **Prompt 版本** | 支持不同场景的 Prompt 模板 |

---

## ❌ Context Engine 不负责

| 职责 | 归属 | 原因 |
|------|------|------|
| 长期记忆存储 | Memory | Memory 是数据层 |
| 记忆搜索/召回 | Memory | Context Engine 读取 Memory 结果 |
| 对话消息持久化 | Session (Runtime) | Runtime 管理 Session |
| 工具执行 | Capability (Runtime) | Context Engine 只注入工具列表 |
| 任务状态管理 | Planner | Planner 管理 Task/Step |
| 权限判断 | Governor | Governor 注入权限约束 |
| LLM 调用 | Scheduler | Scheduler 使用 Context Engine 的输出 |

---

## 与 Memory 的精确边界 ★

```
┌─────────────────────────────────────────────────┐
│                                                 │
│   Memory                         Context Engine │
│   (长期记忆)                     (会话上下文)    │
│                                                 │
│   存储:                           不存储:        │
│     - Session 摘要                 - 任何数据    │
│     - 提取的 experiences                         │
│     - 关键词索引                  读取:           │
│     - 向量嵌入 (未来)              - Memory 召回  │
│                                                 │
│   提供:                           决定:          │
│     - query(msg, top_n)            - 取几条      │
│     - 返回相关记忆                 - 放哪层      │
│                                   - 占多少 Token │
│                                                 │
│   类比: 数据库                     类比: ORM      │
└─────────────────────────────────────────────────┘

数据流:
  Memory.query(msg) → [summary, ...]
      ↓
  ContextEngine (决定取前 3 条, 分配 900 tokens)
      ↓
  拼入 Layer 3: Memory Recall
```

---

## 与其他模块边界

```
Runtime → ContextEngine.build(messages, session, goal)
              ↓
         ContextEngine 从各模块读取:
           - Memory.query()          → Layer 3
           - Governor.get_policy()   → Layer 2
           - Planner.get_status()    → Layer 4
           - CapabilityRegistry.list() → Layer 5
           - Session.history         → Layer 6
           - Runtime.current         → Layer 7-8
              ↓
         返回: [System, Governor, Memory, Planner, Tools, History, Active, User]
              ↓
         → Scheduler.dispatch(prompt)
```

## Context Engine 不重复的原则

- 不存数据 → Memory/Session 负责
- 不搜数据 → Memory 负责搜索
- 不判对错 → Governor 负责
- 不拆任务 → Planner 负责
- 只做一件事: **把正确的东西放进 Prompt**
