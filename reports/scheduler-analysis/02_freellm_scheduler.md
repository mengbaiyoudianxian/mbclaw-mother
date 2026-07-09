# 任务二：FreeLLMAPI Scheduler 分析

## 核心架构

```
FreeLLMAPI router.ts → 最接近 MBclaw 需求的 Scheduler 参考
```

## 路由算法（可直接借鉴）

```
routeRequest(estimatedTokens, skipKeys, preferredModelDbId):
  1. 读取 fallback_config 表 (按 priority 排序)
  2. 加上动态 penalty (429 → penalty+3, 2分钟衰减)
  3. 按 effectivePriority = base + penalty 重排
  4. Sticky session: 优先 preferredModelDbId
  5. 遍历 sortedChain:
     a. 检查 model enabled
     b. 获取 provider
     c. 获取该 platform 的 enabled keys (status=healthy/unknown)
     d. Round-robin 遍历 keys:
        - 跳过 skipKeys
        - 检查 cooldown
        - 检查 rate limit (rpm/rpd/tpm/tpd)
        - 解密 key
        - 成功 → 返回 RouteResult
     e. 该 model 所有 key 不可用 → 继续下一个 model
  6. 全部耗尽 → throw 429
```

## 可直接借鉴的模块

| FreeLLMAPI 文件 | 类/函数 | MBclaw Scheduler | 借鉴原因 |
|---------------|---------|-----------------|---------|
| `services/router.ts` | `routeRequest()` | `scheduler.dispatch()` | 完整路由算法 |
| `services/router.ts` | `recordRateLimitHit()` | `scheduler.record_429()` | 429 惩罚机制 |
| `services/router.ts` | `recordSuccess()` | `scheduler.record_success()` | 成功恢复机制 |
| `services/router.ts` | `getPenalty()` | `scheduler.get_penalty()` | 时间衰减 |
| `services/health.ts` | `checkKeyHealth()` | `scheduler.health_check()` | Key 健康检查 |
| `services/health.ts` | `checkAllKeys()` | `scheduler.health_check_all()` | 定期全量检查 |
| `services/ratelimit.ts` | `canMakeRequest()` | `scheduler.rate_limit_check()` | 滑动窗口限流 |
| `services/ratelimit.ts` | `isOnCooldown()` | `scheduler.cooldown()` | Cooldown 判断 |
| `routes/fallback.ts` | `getAllPenalties()` | `scheduler.get_penalties()` | 暴露惩罚状态 |

### 核心设计：动态惩罚 + 时间衰减

```python
# FreeLLMAPI 的 429 惩罚机制 → MBclaw 直接抄
PENALTY_PER_429 = 3      # 每次 429 增加 3 位优先级
MAX_PENALTY = 10          # 上限
DECAY_INTERVAL = 120s     # 每 2 分钟衰减 1
DECAY_AMOUNT = 1

# 效果:
# model A 遇到 429 → penalty=3 → 排序后移 3 位
# 2 分钟后 → penalty=2 → 恢复 1 位
# 4 分钟后 → penalty=0 → 完全恢复
```

### 核心设计：Sticky Session

```python
# 同一会话优先用同一个 model（避免模型切换导致幻觉）
if preferredModelDbId:
    # 将该 model 移到 fallback chain 最前面
    sortedChain.insert(0, sortedChain.pop(idx))
```

## 不能借鉴的

| FreeLLMAPI 设计 | 原因 |
|----------------|------|
| Express.js 路由层 | MBclaw 用 FastAPI |
| SQLite 直连 (better-sqlite3) | MBclaw 用 SQLAlchemy |
| Key 加密/解密 | TokenPool 已有自己的存储 |
| TypeScript 类型系统 | Python 不同 |

## 推荐指数

★★★★★ — **最佳参考**。路由算法、惩罚机制、健康检查、Rate Limit 全部可抄。
