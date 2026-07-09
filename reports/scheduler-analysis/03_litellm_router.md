# 任务三：LiteLLM Router 分析

## 核心发现

LiteLLM Router 是一个**生产级 LLM 网关**（13 万行 router.py），90% 功能 MBclaw 不需要。

## LiteLLM Router 能力矩阵

| 能力 | LiteLLM 实现 | MBclaw 需要？ |
|------|-------------|:---:|
| **Cooldown** | `_set_cooldown_deployments()` — 自动 cooldown 失败的 deployment | ✅ |
| **Cooldown 恢复** | 指数退避 + 自动恢复 | ✅ |
| **Retry** | `get_num_retries_from_retry_policy()` | ✅ |
| **Fallback** | `get_fallback_model_group()` — 多级 fallback | ✅ |
| **Rate Limit** | Token-level TPM/RPM IO rate limit | ✅ |
| **Health Check** | 定期探测 + 自动 disable | ✅ |
| **Load Balancing** | Weight-based / Round-Robin / Least Busy | 🟡 |
| **Caching** | Redis/S3 缓存 | ❌ |
| **Budget Manager** | 月度预算管理 | ❌ |
| **Spend Tracking** | 精确计费 | ❌ |
| **Callbacks** | 40+ hook 点 | ❌ |
| **Streaming** | SSE streaming + token counting | 🟡 |
| **Guardrails** | 内容过滤 | ❌ |
| **Multi-Deployment** | 同 model 多 deployment | ❌ |
| **Alerting** | Slack/email/webhook | ❌ |

## 值得参考的模块

| LiteLLM 文件 | 类/函数 | 参考什么 | 为什么 |
|-------------|---------|---------|--------|
| `router_utils/cooldown_handlers.py` | `_is_cooldown_required()` | 判断是否需要 cooldown | 逻辑清晰 |
| `router_utils/cooldown_handlers.py` | `_set_cooldown_deployments()` | Cooldown 实现 | 指数退避 |
| `router_utils/cooldown_cache.py` | `CooldownCache` | 内存缓存 cooldown 状态 | 高性能 |
| `router_utils/get_retry_from_policy.py` | `get_num_retries_from_retry_policy()` | 重试次数计算 | 通用算法 |
| `router_utils/fallback_event_handlers.py` | `get_fallback_model_group()` | 多级 fallback | 简单实用 |
| `router_utils/pre_call_checks/model_rate_limit_check.py` | Rate limit check | 调用前检查 | 规则明确 |

## 太重的部分（不参考）

| 模块 | 原因 |
|------|------|
| `router.py` 主体 (13000+ 行) | 企业级网关，MBclaw 不需要 |
| `router_strategy/` (4 种路由策略) | 自动路由/复杂度路由/质量路由/自适应 — 过度设计 |
| `budget_manager.py` | 计费/预算 — MBclaw 不需要 |
| `caching/` | Redis/S3 缓存 — 单实例不需要 |
| `guardrails/` | 内容审核 — 不需要 |
| `callbacks/` | 40+ hook — 过度 |
| `spend_tracking/` | 精确计费 — TokenPool 只统计 |
| `alerting/` | 告警 — 不需要 |

## Cooldown 实现（抄袭重点）

```python
# LiteLLM cooldown 逻辑 → MBclaw 简化版
DEFAULT_COOLDOWN_TIME_SECONDS = 30
DEFAULT_FAILURE_THRESHOLD_MINIMUM_REQUESTS = 5
DEFAULT_FAILURE_THRESHOLD_PERCENT = 0.5  # 50% 失败率触发

def _is_cooldown_required(model_id, exception_status):
    if exception_status == 429:
        return True
    if exception_status >= 500:
        return True
    # APIConnectionError → 不 cooldown (网络问题，不是 key 问题)
    return False
```

## 推荐指数

★★★☆☆ — Cooldown + Retry 值得参考，但整体架构太重
