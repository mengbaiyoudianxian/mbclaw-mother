# 任务五：MBclaw Scheduler 职责设计

> 仅输出职责，不写实现

## Scheduler 核心定位

Scheduler = 母体的"调度大脑"，负责每个 Step 的"找谁做"和"失败了怎么办"。

```
Planner → Scheduler → Capability/LLM → Observation → Planner

Scheduler 的边界:
  ✅ Provider/Key/Model 选择
  ✅ HTTP 调用与重试
  ✅ 故障转移 (fallback)
  ✅ Cooldown 管理
  ✅ Rate limit 管理
  ✅ 执行指标收集

  ❌ 不涉及 Task 分解 (Planner)
  ❌ 不涉及权限判断 (Governor)
  ❌ 不涉及工具具体实现 (Capability)
  ❌ 不涉及 Key 存储 (TokenPool)
```

## Scheduler 流程

```
Receive Task (from Planner)
    │
    ▼
[Evaluate]
    分析 Task 类型:
    ├── LLM_CALL → 需要 Provider + Key + Model
    ├── TOOL_CALL → 需要 Capability (直接执行，不经过 LLM)
    └── REPLY → 直接返回 (不经过 Scheduler)
    │
    ▼
[Choose Worker]
    LLMWorker: 调用 LLM API
    ToolWorker: 通过 CapabilityRegistry 执行
    │
    ▼  (仅 LLM_CALL)
[Choose Provider]
    从 TokenPool 获取可用 Provider 列表
    按优先级排序 + 动态 penalty
    Sticky session: 同会话优先同一 Provider
    │
    ▼
[Choose Key]
    在选定的 Provider 下选择 Key:
    Round-robin 轮询
    跳过 cooldown 中的 key
    跳过 rate-limited 的 key
    │
    ▼
[Dispatch]
    执行调用:
    LLM: HTTP POST → 解析响应
    Tool: CapabilityRegistry.execute()
    │
    ▼
[Monitor]
    收集结果:
    ├── 200 → success → 记录 metrics
    ├── 429 → rate_limited → record 429 penalty → cooldown key → retry
    ├── 5xx → server_error → cooldown key → retry
    ├── timeout → network_error → 不 cooldown → retry
    └── 4xx (非429) → bad_request → abort (不重试)
    │
    ▼
[Retry / Failover]
    if 429 or 5xx or timeout:
      ├── 同 provider 不同 key → Round-robin 下一个
      ├── 同 key 全部不可用 → 下一个 provider (fallback chain)
      └── 全部 provider 不可用 → 等待 cooldown 恢复 → retry
    │
    ▼
[Complete]
    成功或最终失败 → 返回 Observation 给 Planner
```

## Scheduler 管理的资源

| 资源 | 来源 | 管理方式 |
|------|------|---------|
| Provider 列表 | TokenPool | Priority + Dynamic Penalty |
| Key 列表 | TokenPool | Round-Robin + Cooldown |
| Model 列表 | TokenPool | Fallback Chain |
| Cooldown 状态 | Scheduler 内存 | TTL Cache |
| Rate limit 计数 | Scheduler 内存 | Sliding Window |
| Session sticky | Scheduler 内存 | Map[session_id → provider_id] |
| metrics | Scheduler → TokenPool | Usage count + error count |

## 不与以下模块重复

| 模块 | 明确不负责 |
|------|-----------|
| Governor | 不判断操作是否允许，只判断 Provider/Key 是否可用 |
| Planner | 不分解任务，只接受 Step 并按调度策略执行 |
| TokenPool | 不存储 Key，只读取和路由 |
| Runtime | 不管理 Session，不构建 Prompt |
| Capability | 不实现工具，只路由到对应 Capability |
