# 任务七：Scheduler 生命周期

## 完整生命周期

```
Planner → Scheduler
    │
    ▼
[1] Receive Task
    接收: Step {type: LLM_CALL|TOOL_CALL, content, context}
    │
    ▼
[2] Evaluate
    判断 Step 类型:
    ├── LLM_CALL:
    │   ├── 需要 Provider 选择 → [3]
    │   ├── 需要 Key 选择 → [4]
    │   └── 需要 Cooldown/RateLimit 检查 → [5]
    │
    ├── TOOL_CALL:
    │   ├── 本地工具 → 直接 Capability.execute()
    │   ├── 设备工具 → DeviceWorker (检查在线)
    │   └── 外部 API → CapabilityRegistry
    │   └── 不需要 Provider/Key → 跳转到 [6]
    │
    └── REPLY:
        └── 不需要调度 → 直接返回
    │
    ▼  (LLM_CALL only)
[3] Choose Provider
    1. 获取 fallback chain: TokenPool → Provider 列表按 priority 排序
    2. 动态 penalty 调整
    3. Sticky session 检查 (同会话优先同一 Provider)
    4. 排除已耗尽的 Provider (本次请求已全部失败)
    5. 选择第一个可用 Provider
    失败: 全部 Provider 不可用 → [7] failover
    │
    ▼
[4] Choose Key
    1. 获取该 Provider 下所有 Key (status=healthy/unknown)
    2. Round-robin 选择下一个 Key
    3. 跳过 cooldown 中的 Key
    4. Rate limit 检查
    5. 解密/验证 Key
    失败: 该 Provider 所有 Key 不可用 → 返回 [3] 选下一个 Provider
    │
    ▼
[5] Pre-flight Checks
    ├── Cooldown 检查: key 是否在冷却中？
    │   └── 是 → 跳过, 返回 [4]
    ├── Rate Limit 检查: rpm/tpm 是否超限？
    │   └── 是 → 跳过, 返回 [4]
    └── Key 验证: 解密 + 格式检查
        └── 失败 → 标记 key 为 error, 返回 [4]
    │
    ▼
[6] Dispatch
    执行调用:
    ├── LLM: HTTP POST /chat/completions
    │   timeout: 15s (可配)
    │   streaming: 可选
    │
    └── Tool: CapabilityRegistry.execute(name, params)
        timeout: 工具自身控制
    │
    ▼
[7] Monitor
    收集响应:
    ├── 200 OK:
    │   ├── record_success(key, latency)
    │   ├── decay penalty (成功一次减 1)
    │   └── → [10] Complete
    │
    ├── 429 Rate Limited:
    │   ├── record_429(key)
    │   ├── penalty += 3
    │   ├── cooldown key (30s)
    │   └── → [8] Retry
    │
    ├── 5xx Server Error:
    │   ├── record_error(key, 5xx)
    │   ├── cooldown key (30s)
    │   └── → [8] Retry
    │
    ├── timeout:
    │   ├── NO cooldown (网络问题 ≠ key 问题)
    │   └── → [8] Retry
    │
    └── 4xx (非 429) Bad Request:
        ├── abort (请求有问题，重试无意义)
        └── → [10] Complete (error)
    │
    ▼
[8] Retry
    判断:
    ├── 同 Provider 还有可用 Key?
    │   └── → [4] Choose Key (下一个)
    ├── fallback chain 还有 Provider?
    │   └── → [3] Choose Provider (下一个)
    ├── 重试次数未超限?
    │   ├── wait (指数退避: 1s, 2s, 4s, 8s...)
    │   └── → 重试 (cooldown 到期后)
    └── 全部耗尽?
        └── → [9] Failover
    │
    ▼
[9] Failover
    最终手段:
    ├── 降级模型 (complex → simple)
    ├── 降级 Provider (paid → free)
    ├── 返回缓存结果 (如有)
    └── 返回错误 (无可用的 LLM)
    │
    ▼
[10] Complete
    返回 Observation:
    ├── success: {result, tool, latency, tokens, provider, model}
    ├── error: {error, reason, retries_attempted}
    └── 移交给 Planner (决定继续/重规划/终止)
```

## 状态机

```
receiving → evaluating
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
LLM_CALL  TOOL_CALL  REPLY
    │         │         │
    ▼         │         ▼
choosing     │      completed
provider     │
    │         │
    ▼         │
choosing     │
key          │
    │         │
    ▼         ▼
dispatching ──→ monitoring
    ↑              │
    │    ┌─────────┼──────────┐
    │    ▼         ▼          ▼
    │  success  retryable  fatal
    │    │         │          │
    │    │         ▼          │
    │    │      retrying      │
    │    │         │          │
    │    └─────────┘          │
    │         │               │
    │         ▼               │
    │     failover            │
    │         │               │
    └─────────┴───────────────┘
              │
              ▼
          completed
```

## 关键时间参数

| 参数 | 值 | 来源 |
|------|-----|------|
| HTTP timeout | 15s | mother_runtime 当前值 |
| Cooldown duration | 30s | LiteLLM |
| 429 penalty | +3 priority | FreeLLMAPI |
| Max penalty | 10 | FreeLLMAPI |
| Penalty decay | -1 / 2min | FreeLLMAPI |
| Retry max | 4 (同 provider key 数上限) | mother_runtime 当前值 |
| Retry backoff | 1s, 2s, 4s, 8s (指数) | 新设计 |
| Health check interval | 5min | FreeLLMAPI |
