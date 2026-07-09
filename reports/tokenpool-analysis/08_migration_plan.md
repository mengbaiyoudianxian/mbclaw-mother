# 任务八：TokenPool 迁移计划

> 注意：当前 token_pool.py 只有 160 行，需从零建立完整的资源池管理。

---

## Phase 1 — ORM 模型 + Provider 注册（1 天）

### 目标
将 PoolKey dataclass + ModelProfile 统一为 Provider + ProviderKey ORM

### 新增
```
tokenpool/__init__.py
tokenpool/models.py              ← Provider + ProviderKey + KeyMetrics 表
tokenpool/registry.py            ← ProviderRegistry (替代 providers.py)
tokenpool/loader.py              ← KeyLoader (替代 token_pool.py _load)
```

### DB 迁移
```
新建表:
  providers           (Provider 配置)
  provider_keys       (Key 管理, 替代心跳文件扫描)
  key_metrics         (每 Key 每日统计)
  key_metrics_daily   (每日汇总)

种子数据:
  从 BUILTIN_PROVIDERS 迁移 → providers 表
  从 ModelProfile 迁移 → providers 表
  从心跳文件迁移 → provider_keys 表
  从 miclaw_instances 迁移 → provider_keys 表
```

### 删除
```
pool.py PoolKey dataclass      → 移入 models.py ProviderKey
providers.py BUILTIN_PROVIDERS → 移入 registry.py seed_defaults
providers.py seed_default_providers() → 同上
models.py ModelProfile         → 迁移到 Provider 表
```

### 修改
```
token_pool.py: 改为从 TokenPool (新) 读取，保持 API 兼容
llm.py: LLMClient 从 TokenPool (新) 读取
mother_runtime.py: _build_candidates 从 TokenPool (新) 读取
```

### Phase 1 完成标准
- Provider + ProviderKey 表建立
- 所有现有 Key 迁移到 DB
- TokenPool.get_keys() 返回 [ProviderKey]
- 旧的 token_pool.py 标记 deprecated

---

## Phase 2 — 健康检查 + 评分（1 天）

### 目标
从简单的 test_key() 升级为完整的 HealthChecker + KeyScorer

### 新增
```
tokenpool/health.py              ← HealthChecker
tokenpool/scoring.py             ← KeyScorer
```

### 修改
```
tokenpool/loader.py: upsert() 后自动触发 initial test
tokenpool/pool.py: get_keys() 返回排好序 + 带 health_score 的 Key 列表
```

### Phase 2 完成标准
- 每 5 分钟全量健康检查
- health_score 计算 (latency + success_rate + penalty)
- 连续 3 次 invalid → disabled
- load 时自动首次测试

---

## Phase 3 — Metrics + Budget + Rate Limit（1.5 天）

### 目标
细粒度用量统计 + 预算控制 + 速率限制

### 新增
```
tokenpool/metrics.py             ← MetricsCollector
tokenpool/budget.py              ← BudgetManager
tokenpool/ratelimit.py           ← RateLimitConfig (配置层)
```

### 修改
```
admin/router.py: record_request → 委托给 TokenPool.metrics
tokenpool/pool.py: get_keys() 加入 budget_check + rate_limit_check
```

### Phase 3 完成标准
- 每 Key 每日期统计 (KeyMetrics 表)
- 昨日用量查询
- 每日/每月 Token 限额
- RPM/TPM 限制配置
- 超限自动跳过

---

## Phase 4 — Cooldown + Circuit Breaker（1 天）

### 目标
智能故障处理

### 新增
```
tokenpool/cooldown.py            ← CooldownStore
tokenpool/circuit.py             ← CircuitBreaker
```

### 修改
```
tokenpool/pool.py: 与 Scheduler 配合，cooldown 中 Key 不返回
tokenpool/health.py: 加入 auto-recovery (penalty 衰减)
```

### Phase 4 完成标准
- 429/5xx → cooldown Key
- 连续失败 → circuit breaker 触发
- 时间衰减 + 成功恢复 → 自动恢复

---

## Phase 5 — 管理 API + Admin Panel（1 天）

### 目标
管理面板可以通过 API 全量管理 TokenPool

### 新增
```
tokenpool/api.py                 ← 管理端点
```

### Phase 5 完成标准
- GET/POST/DELETE/PATCH /tokenpool/keys
- GET /tokenpool/providers
- GET /tokenpool/stats/*
- 管理面板接入新 API
- 旧 admin/router.py 统计端点标记 deprecated

---

## Phase 6 — 商业 Token Pool 能力（1.5 天）

### 目标
用户贡献比例 + 商业化中转站基础

### 新增
```
tokenpool/commercial.py          ← 商业化逻辑 (可选模块)
```

### 功能
- contribution_ratio 配置 (5%/10%/20%)
- 用户 Token 贡献比自动限流
- 按 owner_code 隔离统计
- 昨日 Token 使用量展示
- 每 Key 每 Model 细粒度统计

### Phase 6 完成标准
- 用户贡献 Key 自动限流 (按 contribution_ratio)
- Admin 面板展示昨日每 Key 贡献量
- 商业化 API 端点 (如需要: POST /v1/token/estimate)

---

## 工作量汇总

| Phase | 内容 | 天数 | 依赖 |
|-------|------|------|------|
| Phase 1 | ORM + Provider + Loader | 1 天 | 无 |
| Phase 2 | Health + Scoring | 1 天 | Phase 1 |
| Phase 3 | Metrics + Budget + Rate Limit | 1.5 天 | Phase 2 |
| Phase 4 | Cooldown + Circuit Breaker | 1 天 | Phase 3 |
| Phase 5 | Admin API | 1 天 | Phase 4 |
| Phase 6 | 商业 Token Pool | 1.5 天 | Phase 5 |
| **总计** | | **7 天** | |

## 影响范围

| 文件 | Phase 1 | Phase 2-4 | Phase 5-6 |
|------|---------|-----------|-----------|
| token_pool.py | deprecated → 删除 | ❌ 删除 | — |
| providers.py | deprecated → 删除 | ❌ 删除 | — |
| models.py ModelProfile | ❌ 删除 (迁移) | — | — |
| tokenpool/ | ✨ 新建 4 文件 | ✨ 新建 6 文件 | ✨ 新建 1 文件 |
| admin/router.py | — | ✏️ 改统计 | ✏️ 接入新 API |
| llm.py | ✏️ 改用新 TokenPool | — | — |
| mother_runtime.py | ✏️ 改用新 TokenPool | — | — |

## MiClaw 建议

MiClaw Bridge 最终应作为 TokenPool 的一个 **free_proxy** Provider：

```
当前: bridge_manager.py → 独立系统，直接转发
目标: tokenpool → Provider(type=free_proxy, name="miclaw-bridge")
      → ProviderKey(base_url="http://47.83.2.188/bridge/miclaw/v1")
      → Scheduler 将其作为 fallback chain 最后一环
      → bridge_manager.py 只负责实例登录/验证
```

理由: MiClaw Bridge 本质是一个 LLM API 端点，应通过 TokenPool 统一管理，而非作为独立 Gateway。
