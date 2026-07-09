# 任务二：FreeLLMAPI 设计分析

## 核心发现

FreeLLMAPI 的 SQLite 存储 + 内存惩罚 + 滑动窗口限流 是 MBclaw TokenPool 的最佳参考。
它的 router.ts 已在 Scheduler 分析中详述（参见 `reports/scheduler-analysis/02_freellm_scheduler.md`），
本章聚焦 TokenPool 数据层设计。

---

## FreeLLMAPI 数据模型

### models 表
```
id, platform, model_id, display_name,
intelligence_rank, speed_rank, size_label,
rpm_limit, rpd_limit, tpm_limit, tpd_limit,
monthly_token_budget, enabled
```

### api_keys 表
```
id, platform, encrypted_key, iv, auth_tag,
status (healthy/invalid/error/unknown),
enabled, last_checked_at
```

### fallback_config 表
```
model_db_id, priority, enabled
```

### rate_limit_usage 表 (滑动窗口)
```
platform, model_id, key_id, kind (request/tokens),
tokens, created_at_ms
→ 自动清理 24 小时前的记录
```

---

## 可直接借鉴的模块

| FreeLLMAPI 文件 | 类/函数 | 翻译为 Python | 用途 |
|---------------|---------|-------------|------|
| `services/router.ts` | `routeRequest()` | `tokenpool/router.py` | 完整路由逻辑 |
| `services/health.ts` | `checkKeyHealth()` | `tokenpool/health.py` | Key 健康检查 |
| `services/health.ts` | `checkAllKeys()` | `tokenpool/health.py` | 批量健康检查 |
| `services/ratelimit.ts` | `canMakeRequest()` | `tokenpool/ratelimit.py` | 滑动窗口限流 |
| `services/ratelimit.ts` | `recordUsage()` | `tokenpool/metrics.py` | 用量记录 |
| `services/ratelimit.ts` | `isOnCooldown()` | `tokenpool/cooldown.py` | Cooldown 判断 |
| `routes/fallback.ts` | fallbackConfig CRUD | `tokenpool/fallback.py` | fallback 链管理 |

## 建议直接翻译的设计

### 1. Dynamic Penalty + 时间衰减
```
Penalty 机制 (router.ts L46-104):
  PENALTY_PER_429 = 3
  MAX_PENALTY = 10
  DECAY_INTERVAL_MS = 120s
  DECAY_AMOUNT = 1

→ tokenpool/scoring.py:
  class PenaltyManager:
      hit(key_id) → penalty +3
      decay(key_id) → penalty -1 every 120s
      get(key_id) → current penalty
```

### 2. 健康检查 + 自动禁用
```
Health (health.ts):
  CONSECUTIVE_FAILURES_TO_DISABLE = 3
  CHECK_INTERVAL_MS = 5min
  validateKey → 401/403 → disabled
  Transport error → status=error (不 disable)

→ tokenpool/health.py:
  class HealthChecker:
      check(key) → healthy/invalid/error
      连续 3 次 invalid → enabled=False
      Transport error → 不计数
```

### 3. 滑动窗口限流
```
RateLimit (ratelimit.ts):
  canMakeRequest(platform, modelId, keyId, limits) → bool
    检查 rpm/rpd/tpm/tpd 四维限制
  recordUsage() → 写入 + 清理 24h 前记录

→ tokenpool/ratelimit.py:
  class SlidingWindowRateLimiter:
      check(key_id, estimated_tokens) → bool
      record(key_id, actual_tokens)
      cleanup() → 清理过期记录
```

## 不能借鉴的

| FreeLLMAPI 设计 | 原因 |
|----------------|------|
| better-sqlite3 同步 API | MBclaw 用 SQLAlchemy |
| Key AES-256-GCM 加密 | TokenPool 不需要加密（本地存储） |
| Express.js 路由 | FastAPI 不同 |
| TypeScript Map 内存存储 | Python 用 dict + threading.Lock |

## 推荐指数

★★★★★ — 数据模型 + 惩罚机制 + 健康检查 + 限流 — 全部可抄
