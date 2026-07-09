# 任务六：Scheduler 目录设计

```
scheduler/
├── __init__.py          导出 Scheduler
├── scheduler.py         主 Scheduler 类
│   class Scheduler:
│       dispatch(task) → Observation
│       职责: 接收 Task → 选择 Worker → 路由 Provider/Key → 调用 → 返回结果
│       流程: evaluate → choose → dispatch → monitor → retry/failover → complete
│
├── router.py            LLM 路由
│   class LLMRouter:
│       route(model_preference, session_id) → RouteResult
│       职责: 从 TokenPool 选择最优 Provider + Key
│       算法: Priority + Dynamic Penalty + Round-Robin + Sticky Session
│       来源: 借鉴 FreeLLMAPI router.ts routeRequest()
│       替代: mother_runtime._build_candidates() + providers.get_best_client()
│
├── provider.py          Provider 管理
│   class ProviderManager:
│       list_available() → [(provider_id, priority, status)]
│       get_fallback_chain() → [provider_id]  (按 priority 排序)
│       职责: 读取 Provider 配置，返回可用列表
│       来源: 替代 providers.py get_best_client() 的 provider 选择部分
│
├── key_selector.py      Key 选择
│   class KeySelector:
│       select(provider_id, skip_keys) → Key
│       策略: Round-Robin + cooldown 跳过
│       职责: 在选定 Provider 下选一个可用 Key
│       来源: 参考 FreeLLMAPI router.ts Round-Robin 部分
│
├── cooldown.py          Cooldown 管理
│   class CooldownManager:
│       cooldown(key_id, reason, duration)
│       is_cooled_down(key_id) → bool
│       recover(key_id)
│       职责: 管理 key 的 cooldown 状态 (内存 TTL)
│       来源: 参考 LiteLLM cooldown_handlers.py + FreeLLMAPI ratelimit.ts
│
├── ratelimit.py         速率限制
│   class RateLimiter:
│       can_proceed(key_id, estimated_tokens) → bool
│       record_usage(key_id, tokens)
│       职责: 滑动窗口速率限制 (rpm/tpm)
│       来源: 参考 FreeLLMAPI ratelimit.ts
│
├── retry.py             重试策略
│   class RetryPolicy:
│       should_retry(status_code, attempt) → bool
│       next_delay(attempt) → seconds  (指数退避)
│       职责: 决定是否重试、等待多久
│       规则: 429→retry, 5xx→retry, timeout→retry, 4xx→abort
│       来源: 参考 LiteLLM get_num_retries_from_retry_policy()
│
├── fallback.py          故障转移
│   class FallbackManager:
│       get_fallback_chain(exhausted_providers) → [Provider]
│       next_fallback(exhausted) → Provider | None
│       职责: 管理多级 fallback 链
│       来源: 参考 FreeLLMAPI fallback.ts + LiteLLM get_fallback_model_group()
│
├── health.py            健康检查
│   class HealthChecker:
│       check_key(key) → healthy | degraded | dead
│       check_all() → 批量检查
│       职责: 定期探测 key 可用性 (最小请求 1 token)
│       来源: 参考 FreeLLMAPI health.ts
│
├── metrics.py           执行指标
│   class SchedulerMetrics:
│       record_success(key_id, latency, tokens)
│       record_error(key_id, status_code, error)
│       record_429(key_id)
│       职责: 收集执行指标
│       来源: 替代 tools.py bump_usage() + mother_runtime.py 内联统计
│
└── sticky.py            Sticky Session
    class StickySession:
        get_preferred(session_id) → provider_id | None
        set_preferred(session_id, provider_id)
        职责: 同一会话优先同一 Provider (减少模型切换幻觉)
        来源: 参考 FreeLLMAPI preferredModelDbId
```

## 各文件职责精简

| 文件 | 职责 | 来源 | 替代 |
|------|------|------|------|
| scheduler.py | 统筹调度 | 新设计 | agent_run + mother_runtime 的 LLM 调用部分 |
| router.py | LLM 路由选择 | FreeLLMAPI routeRequest() | _build_candidates() + LLM for 循环 |
| provider.py | Provider 管理 | providers.py 简化版 | get_best_client() |
| key_selector.py | Round-Robin Key 选择 | FreeLLMAPI RR 部分 | 新功能 |
| cooldown.py | Cooldown 管理 | LiteLLM cooldown | 新功能 |
| ratelimit.py | 速率限制 | FreeLLMAPI ratelimit | 新功能 |
| retry.py | 重试策略 | LiteLLM retry_policy | 内联重试逻辑 |
| fallback.py | 故障转移链 | FreeLLMAPI fallback.ts | _build_candidates 的 provider 遍历 |
| health.py | 健康检查 | FreeLLMAPI health.ts | 新功能 |
| metrics.py | 执行指标 | 新设计 | bump_usage() 内联统计 |
| sticky.py | 会话粘性 | FreeLLMAPI preferredModelDbId | 新功能 |
