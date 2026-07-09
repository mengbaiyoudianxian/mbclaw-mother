# 任务八：Scheduler 迁移计划

---

## Phase 1 — 统一 LLM 调用入口（1 天）

### 目标
消除 3 处独立 httpx 调用，统一为一个 Scheduler.dispatch()

### 删除
```
agent.py:122 直接 httpx.post     → 移入 scheduler.dispatch()
mother_runtime.py:215 直接 httpx  → 移入 scheduler.dispatch()
providers.py get_best_client() LLM Client 创建 → 移入 scheduler
```

### 新增
```
scheduler/__init__.py
scheduler/scheduler.py           ← Scheduler 主类
scheduler/provider.py            ← ProviderManager (简化 providers.py)
scheduler/metrics.py             ← SchedulerMetrics
```

### 修改
```
agent.py agent_run(): llm 调用 → scheduler.dispatch(LLM_CALL, ...)
mother_runtime.py run(): httpx 调用 → scheduler.dispatch(LLM_CALL, ...)
```

### Phase 1 完成标准
- 所有 LLM 调用经过 Scheduler.dispatch()
- 行为与当前完全一致 (无新功能，仅统一入口)
- 停止直接 httpx

---

## Phase 2 — LLM Router（1.5 天）

### 目标
实现完整的 LLM 路由：优先级 + Round-Robin + Sticky Session

### 新增
```
scheduler/router.py              ← LLMRouter (核心)
scheduler/key_selector.py        ← KeySelector (Round-Robin)
scheduler/sticky.py              ← StickySession
```

### 删除
```
mother_runtime.py _build_candidates() → 移入 router.py
providers.py get_best_client() 的 provider 选择 → 移入 router.py
```

### Phase 2 完成标准
- Fallback chain 按 priority 排序
- 同 Provider 下 Key Round-Robin
- 同 Session 优先同一 Provider

---

## Phase 3 — Cooldown + Retry + Rate Limit（1.5 天）

### 目标
智能故障处理

### 新增
```
scheduler/cooldown.py            ← CooldownManager
scheduler/retry.py               ← RetryPolicy
scheduler/ratelimit.py           ← RateLimiter
scheduler/fallback.py            ← FallbackManager
```

### 修改
```
scheduler/scheduler.py: dispatch() 后接入 monitor → retry → cooldown
```

### Phase 3 完成标准
- 429/5xx → cooldown key，重试下一个
- 指数退避重试
- 429 动态 penalty 下沉
- 全部 key 不可用 → fallback 降级

---

## Phase 4 — 健康检查 + TokenPool 集成（1 天）

### 目标
定期探测 Key 可用性，与 TokenPool 状态同步

### 新增
```
scheduler/health.py              ← HealthChecker
```

### 修改
```
scheduler/scheduler.py: 启动后台 health check 任务
token_pool.py: Key status 改为由 health check 更新
```

### Phase 4 完成标准
- 每 5 分钟全量检查 Key
- 连续 3 次失败 → 自动 disable
- Health status: healthy/degraded/error
- TokenPool 读取 health status

---

## Phase 5 — Runtime + Planner 接入（1 天）

### 目标
Scheduler 成为 Planner 和 Runtime 之间的唯一 LLM/Tool 调度层

### 修改
```
runtime/loop.py: LLM 调用 → scheduler.dispatch()
runtime/worker.py: Tool 执行 → scheduler.dispatch(TOOL_CALL)
planner/planner.py: 多 Step → 逐个推入 scheduler
```

### Phase 5 完成标准
- Planner → Scheduler → Capability/LLM 完整链路
- 无绕过 Scheduler 的调用
- Governor 在 Scheduler 之前做权限检查

---

## 工作量汇总

| Phase | 内容 | 天数 | 依赖 |
|-------|------|------|------|
| Phase 1 | 统一 LLM 调用入口 | 1 天 | 无 |
| Phase 2 | LLM Router | 1.5 天 | Phase 1 |
| Phase 3 | Cooldown + Retry + Rate Limit | 1.5 天 | Phase 2 |
| Phase 4 | 健康检查 + TokenPool 集成 | 1 天 | Phase 3 |
| Phase 5 | Runtime + Planner 接入 | 1 天 | Phase 4 + Runtime + Planner |
| **总计** | | **6 天** | |

## 影响范围

| 文件 | Phase 1 | Phase 2 | Phase 3-5 |
|------|---------|---------|-----------|
| agent.py | ✏️ 改调用 | — | — |
| mother_runtime.py | ✏️ 改调用 | ❌ 删 _build_candidates | — |
| providers.py | ✏️ 简化 | ❌ 删 provider 选择部分 | — |
| scheduler/ | ✨ 新建 3 文件 | ✨ 新建 3 文件 | ✨ 新建 4 文件 |
| token_pool.py | — | — | ✏️ 接 health check |
| runtime/ | — | — | ✏️ 接入 scheduler |

## 优先级

Scheduler 是 **P1 优先级**（与 Governor 同级，低于 Runtime/P1，高于 Planner/P2）。

原因：
- 当前 3 处独立 LLM 调用，无统一路由
- 无 Cooldown/Retry/Rate Limit → Key 浪费严重
- 但必须先有统一 Runtime (Phase 1) 才能接入 Scheduler
