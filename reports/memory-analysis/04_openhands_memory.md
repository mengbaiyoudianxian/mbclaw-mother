# 任务四：OpenHands Memory 分析

## OpenHands 数据分类

### 属于 Memory（长期保存）

| 数据 | OpenHands 表/模块 | MBclaw 对应 |
|------|------------------|------------|
| Conversation 摘要 | Condenser 压缩输出 → DB | summaries 表 ✅ |
| User Settings | User Settings DB | 缺失 ❌ |
| Plugin 配置 | Plugin Settings | 缺失 ❌ |
| Skill 定义 | Skill Loader → DB | tools 表 (已有的) |

### 属于 Session（当前会话）

| 数据 | OpenHands 表/模块 | MBclaw 对应 |
|------|------------------|------------|
| 对话消息 | Conversation Messages | messages 表 ✅ |
| Agent 状态 | SDK ConversationExecutionStatus | Session.status ✅ |
| Sandbox 状态 | SandboxStatus | 无 (MBclaw 无 Sandbox) |
| Task 状态 | AppConversationStartTask | 缺失 (待 Planner) |

### 属于 Context（当前 Prompt）

| 数据 | OpenHands 模块 | MBclaw 对应 |
|------|---------------|------------|
| Condenser 输出 | Condenser.condense(history) | WorkingMemory 压缩 |
| 当前工具结果 | Observation | mother_runtime 即时追加 |
| 当前文件状态 | Workspace 上下文 | 无 (MBclaw 无 Workspace) |

---

## OpenHands Memory → MBclaw 映射

| OpenHands | 属于 | MBclaw 应存哪里 |
|-----------|------|----------------|
| Conversation 摘要 | Memory | summaries ✅ (已有) |
| User Settings | Memory | user_memories (新建) |
| Plugin/Skill 定义 | Capability | tools/capability 表 (已有) |
| 对话消息 | Session | messages (已有) |
| Agent 状态 | Session | sessions.status (已有) |
| Task 状态 | Session → Planner 管理 | planner/task.py (待建) |
| Condenser 输出 | Context | ContextEngine (待建) |
| 工具结果 | Context | Runtime 即时追加 |
| Workspace 状态 | Runtime | 无 (不需要) |

## 推荐指数

★★☆☆☆ — 数据分类清晰，但大部分实现不可见 (SDK 内部)
