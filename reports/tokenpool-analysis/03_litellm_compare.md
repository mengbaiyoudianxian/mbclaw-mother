# 任务三：LiteLLM 对比分析

## 核心发现

LiteLLM Token 管理是对企业级多租户网关，90% 功能 MBclaw 不需要。
但其 **Cooldown + 重试策略 + deployment 管理** 三个模块值得参考。

---

## LiteLLM Token 管理能力矩阵

| 能力 | LiteLLM 实现 | MBclaw 需要？ |
|------|-------------|:---:|
| Deployment 管理 | Model group → 多 deployment (每个有独立 key) | ✅ |
| Cooldown | `_is_cooldown_required()` + `_set_cooldown_deployments()` | ✅ |
| Retry Policy | `get_num_retries_from_retry_policy()` | ✅ |
| Fallback | `get_fallback_model_group()` | ✅ |
| Rate Limit | IO Token rate limit (request + response) | ✅ |
| Router Strategy | 4 种: auto/complexity/quality/adaptive | ❌ |
| Budget Manager | 月度预算跟踪 | ❌ |
| Spend Tracking | 精确计费 | ❌ |
| Virtual Keys | 虚拟 Key 管理 | ❌ |
| SSO/Auth | Okta/Google OAuth | ❌ |
| Multi-Tenant | 团队/组织隔离 | ❌ |
| Callbacks | 40+ event hooks | ❌ |
| Guardrails | 内容审核 | ❌ |
| Caching | Redis/S3 | ❌ |

## 值得参考的模块

### 1. Cooldown（推荐直接抄思路）

```python
# LiteLLM cooldown_handlers.py → MBclaw tokenpool/cooldown.py
_is_cooldown_required(model_id, exception_status, exception_str):
    if 429: return True
    if 5xx: return True
    if "APIConnectionError" in exception_str: return False  # 网络问题不 cooldown
    return False

_set_cooldown_deployments(model_id, cooldown_time):
    # 指数退避: 30s, 60s, 120s, 240s...
    cooldown_time = min(30 * (2 ** consecutive_failures), 600)  # 10min cap
```

### 2. Retry Policy

```python
# LiteLLM get_retry_from_policy.py → MBclaw scheduler/retry.py
get_num_retries(retry_policy, exception):
    ContentPolicyViolationError → 0 (不重试)
    RateLimitError → policy.num_retries (默认重试)
    APIConnectionError → 1 (网络问题只重试1次)
```

### 3. Deployment → ProviderKey 模型

```python
# LiteLLM deployment → MBclaw ProviderKey
Deployment:
    model_name: str       → model
    litellm_params:
        model: str        → model
        api_key: str      → api_key
        api_base: str     → base_url
        rpm: int          → rpm_limit
        tpm: int          → tpm_limit
        max_retries: int  → max_retries
```

---

## 不要的模块

| 模块 | 原因 |
|------|------|
| `router_strategy/` 4 种策略 | 过度设计，MBclaw 只需要 Fallback Chain + Round-Robin |
| `budget_manager.py` | 企业预算，MBclaw 不需要 |
| `spend_tracking/` | 精确计费，MBclaw 只需要粗粒度统计 |
| `guardrails/` | 内容审核，不属于 TokenPool |
| `caching/` | Redis/S3 缓存，单实例不需要 |
| `a2a_protocol/` | Agent-to-Agent 协议，不属于 TokenPool |
| SSO/Auth | 多租户认证，MBclaw 单用户 |

---

## 推荐指数

★★★☆☆ — Cooldown + Deployment 模型值得参考，但整体架构太重
