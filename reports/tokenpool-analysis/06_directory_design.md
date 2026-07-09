# 任务六：TokenPool 目录设计

```
tokenpool/
├── __init__.py          导出 TokenPool
├── pool.py              主 TokenPool 类
│   class TokenPool:
│       get_keys(filter) → [ProviderKey]
│       get_providers() → [Provider]
│       record_metrics(key_id, result)
│       职责: 统一的资源池查询入口
│       替代: 当前 token_pool.py 的全部功能
│
├── models.py            ORM 模型
│   class Provider(Base)
│   class ProviderKey(Base)
│   class KeyMetrics(Base)
│   class ProviderEndpoint(Base)
│   class DailyTokenBudget(Base)
│       职责: 数据库表定义
│       替代: 当前 models.py ModelProfile + token_pool.py PoolKey
│
├── loader.py            Key 发现与加载
│   class KeyLoader:
│       load_from_heartbeat() → [{base_url, api_key, model, ...}]
│       load_from_miclaw() → [{...}]
│       load_from_db() → [{...}]
│       upsert(keys) → 同步到 DB
│       职责: 从心跳文件/miclaw_instances/DB 发现 Key
│       来源: 替代 token_pool.py _load()
│
├── registry.py          Provider 注册
│   class ProviderRegistry:
│       register(provider: Provider)
│       get(name) → Provider
│       list_all() → [Provider]
│       seed_defaults() → 写入内置 Provider
│       职责: Provider 注册管理
│       来源: 替代 providers.py BUILTIN_PROVIDERS + seed_default_providers()
│
├── health.py            健康检查
│   class HealthChecker:
│       check_key(key) → healthy / degraded / error
│       check_all() → 批量检查
│       auto_disable() → 连续 3 次失败 → disabled
│       职责: Key 可用性主动探测
│       来源: 参考 FreeLLMAPI health.ts
│       新功能 (当前仅有 test_key)
│
├── scoring.py           评分引擎
│   class KeyScorer:
│       score(key, metrics) → health_score (0.0-1.0)
│       维度: latency(0.3) + success_rate(0.5) + penalty(0.2)
│       职责: 计算 Key 综合健康分
│       新功能 (当前无)
│
├── metrics.py           使用指标
│   class MetricsCollector:
│       record(key_id, date, tokens, latency, status)
│       get_daily(key_id, date) → KeyMetrics
│       get_yesterday(key_id) → KeyMetrics
│       get_provider_stats(provider_id) → stats
│       职责: 用量统计
│       来源: 替代 admin/router.py record_request() + 新增每 Key 统计
│
├── budget.py            预算控制
│   class BudgetManager:
│       check(key_id, estimated_tokens) → bool
│       allocate(key_id, tokens)
│       get_remaining(key_id) → tokens
│       职责: 每日/每月 Token 限额控制
│       新功能 (当前无)
│
├── ratelimit.py         速率限制
│   class RateLimitConfig:
│       rpm_limit: int
│       tpm_limit: int
│       职责: 速率限制配置 (存储在 ProviderKey 表中)
│       执行检查在 Scheduler，配置存储在 TokenPool
│
├── cooldown.py          Cooldown 状态
│   class CooldownStore:
│       set_cooldown(key_id, until, reason)
│       is_cooled_down(key_id) → bool
│       get_cooldown(key_id) → (until, reason) | None
│       职责: Cooldown 状态持久化
│       来源: 参考 LiteLLM cooldown_handlers.py
│       新功能 (当前无)
│
├── circuit.py           熔断器
│   class CircuitBreaker:
│       record_error(key_id)
│       record_success(key_id)
│       is_open(key_id) → bool  (熔断: 连续失败 ≥ 3)
│       reset(key_id)
│       职责: 自动熔断 + 自动恢复
│       新功能 (当前无)
│
└── api.py               管理 API
    GET  /tokenpool/keys              → 所有 Key 状态
    GET  /tokenpool/keys/{id}         → Key 详情
    GET  /tokenpool/providers         → Provider 列表
    POST /tokenpool/keys              → 添加 Key
    DELETE /tokenpool/keys/{id}       → 删除 Key
    PATCH /tokenpool/keys/{id}        → 修改 Key 配置
    GET  /tokenpool/stats/daily       → 日统计
    GET  /tokenpool/stats/{id}        → 单 Key 统计
    POST /tokenpool/keys/{id}/enable  → 启用/禁用
    职责: 管理面板的 TokenPool 管理接口
    来源: 替代 admin/router.py 统计端点 + 新增管理端点
```

## 各文件职责精简

| 文件 | 职责 | 来源 | 替代 |
|------|------|------|------|
| pool.py | 资源池主入口 | 新设计 | token_pool.py 全部 |
| models.py | ORM 模型 | 扩展现有 models.py | ModelProfile + PoolKey |
| loader.py | Key 发现 | token_pool.py _load() | _load() 逻辑 |
| registry.py | Provider 注册 | providers.py | BUILTIN_PROVIDERS + seed_default_providers() |
| health.py | 健康检查 | FreeLLMAPI health.ts | token_pool.py test_key() |
| scoring.py | 评分 | 新设计 | 无 |
| metrics.py | 指标 | admin/router.py | record_request() |
| budget.py | 预算 | 新设计 | 无 |
| ratelimit.py | 速率配置 | FreeLLMAPI ratelimit.ts | 无 |
| cooldown.py | Cooldown | LiteLLM cooldown | 无 |
| circuit.py | 熔断 | 新设计 | 无 |
| api.py | 管理 API | 新设计 | admin/router.py 统计 + 新增 |
