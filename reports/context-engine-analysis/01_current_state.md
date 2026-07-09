# 任务一：当前 Context 生命周期

## 结论：有两套独立的 Context 系统

### A. agent_run Context（agent.py `_build_context`）

```
每次 LLM 调用前：
  1. MemoryRepo.query(user_msg, top_n=3)  → FTS5 搜索记忆  [DB IO]
  2. db.query(Message).limit(10)          → 最近 10 条消息  [DB IO]
  3. 拼接为纯文本 string:
     ## 相关记忆
     - [#session_id] summary[:200]
     ## 对话历史
     [用户]: content[:300]
     [助手]: content[:300]
  4. 与 System Prompt 拼接后发送
```

### B. MotherRuntime Context（WorkingMemory + Recall）

```
每次 run() 调用：
  1. WorkingMemory 已缓存 system + messages + recall
  2. MemoryRepo.query(message, 3)  → 写入 wm.set_recall()  [如有 db_factory]
  3. wm.to_messages():
     [system prompt]
     [memory recall]
     [messages[-20:]]  ← 只保留最近 20 条
  4. 压缩触发: 80% token limit → _maybe_compress()
     压缩策略: 取前半消息 → 取最后 3 条拼接 → 插入摘要
```

---

## 当前 Context 组成

| 组成 | agent_run | MotherRuntime | 来源 |
|------|:---:|:---:|------|
| System Prompt | AGENT_PROMPT (短) | SYSTEM_PROMPT (长) | 硬编码字符串 |
| Tool List | list_tools(db) → 动态 | TOOL_DEFS_TEXT → 硬编码 | DB / 字符串 |
| Memory Recall | MemoryRepo FTS5 | MemoryRepo FTS5 | Memory 模块 |
| History (最近消息) | DB Message 表 | WorkingMemory.messages (内存) | DB / 内存 |
| Tool Result | 追加到 current 变量 | 追加到 messages | 即时 |
| User Input | user_message 参数 | message 参数 | 入口 |
| 压缩摘要 | ❌ 无 | [历史摘要 #N] 简单拼接 | WorkingMemory |
| Token 估算 | ❌ 无 | len(text)//4 粗略 | WorkingMemory |

---

## 重复的能力

| 能力 | agent_run | MotherRuntime | 问题 |
|------|-----------|---------------|------|
| System Prompt | AGENT_PROMPT | SYSTEM_PROMPT | 两份 Prompt，内容完全不同 |
| Memory Recall | _build_context L74 | run() L168 | 重复调 MemoryRepo |
| History 加载 | DB Message 表 | WorkingMemory 内存 | 两套存储 |
| Tool List | list_tools(db) | TOOL_DEFS_TEXT | 动态 vs 静态 |

---

## 缺失的能力

| 能力 | 说明 | 严重度 |
|------|------|--------|
| **重要性压缩** | 只按时间截断，不按重要性保留 | 🔴 高 |
| **Token Budget 管理** | 无显式预算分配，只有粗略估算 | 🔴 高 |
| **分层 Prompt** | 所有内容平铺在一个 system message 中 | 🔴 高 |
| **Checkpoint/Restore** | 无保存/恢复上下文 | 🟡 中 |
| **Context 恢复** | 无 LLM 失败后恢复上下文 | 🟡 中 |
| **长会话支持** | 压缩策略粗糙（简单截断+拼接） | 🟡 中 |
| **压缩质量评估** | 不检查压缩后语义完整性 | 🟡 中 |
| **Prompt 版本管理** | 写死代码，不可切换 | 🟢 低 |
| **Context 预热** | 无预热（首次调用才加载 Memory） | 🟢 低 |

---

## 当前 Context 问题

1. **两套 Prompt 内容矛盾**: AGENT_PROMPT 说"短小精炼三句话"，SYSTEM_PROMPT 说"42 项内置技能"
2. **压缩损语义**: `" | ".join(str(m.content[:80]) for m in old[-3:])` 完全丢失语义
3. **无 Token Budget**: 6000 token limit 是硬编码，不根据模型调整
4. **无分层**: System Prompt 里混了角色+规则+工具+技能+示例
5. **Memory Recall 每次调**: 每条消息都 FTS5 搜索，浪费 IO
