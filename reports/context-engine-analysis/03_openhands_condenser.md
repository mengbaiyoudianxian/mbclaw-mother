# 任务三：OpenHands Condenser 分析

## 核心发现

OpenHands Condenser 在 `openhands-sdk` 外部包中，仓库不可见。
但从测试代码和企业版迁移脚本可推断其设计。

---

## OpenHands Condenser 设计（从代码推断）

### Condenser 配置

```python
# 从 migration 文件推断:
condenser_max_size     # 最大压缩后的 token 数
enable_default_condenser  # 是否启用默认压缩
```

### Condenser 工作流程（推断）

```
Agent Loop 每轮:
  1. Condenser.condense(history)  ← 传入完整对话历史
  2. 判断: 当前 token 数 > condenser_max_size?
     ├── 否 → 不压缩，直接返回原 history
     └── 是 → 执行压缩:
          a. 保留最近 N 条消息 (关键上下文)
          b. 旧消息 → LLM 生成摘要
          c. 摘要替换旧消息 → 返回压缩后 history
  3. 压缩后的 history → 发送给 LLM
```

### Conversation 恢复

```python
# 从 app_conversation 服务推断:
Conversation 恢复流程:
  1. 从 DB 加载 Conversation
  2. 加载 associated Task
  3. 从 SDK 获取 Agent 状态 (包括压缩后的 history)
  4. 如果 Agent 仍在运行 → 获取 live status
  5. 如果 Agent 已结束 → 返回最终状态
```

### State 保存

```python
# 从 app_conversation 模型推断:
Conversation 状态保存:
  1. SDK 内部: Agent 状态 (messages, tools, context)
  2. Server 层: Conversation metadata (status, sandbox, user)
  3. 每轮对话后: Status 更新 (RUNNING/WAITING_USER/FINISHED/ERROR)
```

---

## 值得借鉴的设计

| OpenHands 设计 | MBclaw Context Engine | 优先级 |
|---------------|----------------------|--------|
| **LLM 生成压缩摘要** | 压缩时调 LLM 生成语义摘要 → 替代简单拼接 | P0 |
| **condenser_max_size** | Token Budget: 超过阈值才压缩 | P0 |
| **保留最近 N 条** | Compressor: 保留最近消息 + 摘要历史 | P0 |
| **Conversation 状态机** | ContextEngine: 状态管理 (active/compressed/restored/closed) | P1 |
| **SDK 与 Server 状态分离** | ContextEngine 独立于 Runtime | P1 |

## 不能借鉴的

| OpenHands 设计 | 原因 |
|---------------|------|
| Sandbox 关联 | MBclaw 无 Sandbox |
| Live Status (WebSocket) | MBclaw 无实时推送需求 |
| User Settings (DB) | MBclaw 简单场景不需要 |

## 推荐指数

★★★☆☆ — LLM 压缩摘要 + Token Threshold 值得参考
