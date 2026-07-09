# 任务五：MBclaw Runtime 融合设计

> 不重新设计。融合现有代码 + 参考项目精华。

## 目标 Runtime 流程

```
Gateway (QQ/微信/Web/CLI/API)
    │
    ▼
[Receive]  接收 StandardMessage → 路由到 Session
    │
    ▼
[Governor]  ← 预留
    协调整个 Runtime 生命周期
    管理: Session 创建/恢复/暂停/关闭
    调度: 选择 Planner/Scheduler/Worker
    │
    ▼
[Context]  ← 预留
    构建 Prompt:
      1. SystemPrompt (基座角色)
      2. Rules (用户设定)
      3. Capabilities (可用工具列表)
      4. Memory (相关记忆召回)
      5. History (最近消息)
    │
    ▼
[Planner]  ← 预留
    理解意图 → 分解为步骤
    │
    ▼
[Scheduler]  ← 预留
    选择最优 LLM Provider + Model
    故障转移: 重试 → fallback → 降级
    │
    ▼
[Worker]    当前实现 (MotherRuntime._execute_tool)
    执行工具调用:
      Registry.get(tool_name) → validate → execute
    安全策略: allow/deny/ask
    │
    ▼
[Capability]
    统一执行: tool / skill / prompt_skill / mcp_tool
    │
    ▼
[Observation]
    包装工具结果: {type, tool, result, error, duration}
    │
    ▼
[Memory]  ← 预留
    存储: 对话消息 → Session DB
    提取: 会话摘要 → experiences 表
    │
    ▼
[Reply]
    格式化: 按渠道适配 (QQ→去Markdown, Web→保留)
    返回给用户
```

## 融合来源

| 组件 | 现有代码 (保留) | 参考项目 (借鉴) |
|------|---------------|----------------|
| Receive | gateway_agent.py + api.py | OpenClaw channels/ registry |
| Context | WorkingMemory.to_messages() | Claude Prompt Runtime (分层) |
| Worker | MotherRuntime._execute_tool() | Codex CLI execpolicy |
| Observation | tool result 字符串 | OpenHands Observation model |
| Reply | gateway_agent.py 去Markdown | OpenClaw reply-prefix |

## 阶段路线

| 阶段 | 内容 | 来源 |
|------|------|------|
| Phase 1 | 统一 agent_run + MotherRuntime → 单个 Runtime | 现有 |
| Phase 2 | 接入 Capability Registry (替换硬编码工具定义) | Capability |
| Phase 3 | 接入 Context Engine (替换硬编码 Prompt) | 预留 |
| Phase 4 | 接入 Governor (统一生命周期管理) | 预留 |
| Phase 5 | 接入 Scheduler (TokenPool LLM 调度) | 预留 |
