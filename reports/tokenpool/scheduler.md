# TokenPool Scheduler 分析

## 作用

Scheduler 是 TokenPool 的调度核心，负责编排 GuardRail 检查流程，决定哪些 Key 可用于当前请求。

## 三层 GuardRail

### 1. QuotaGuard — Token 配额检查
- 仅对用户共享 Key（心跳贡献）生效
- 计算公式：`today_quota = yesterday_usage × share_percent`
- 今已用量 >= 配额 → 拒绝

### 2. RateLimitGuard — 速率限制检查
- 检查 Key 是否处于冷却状态
- 冷却原因：429 (限速)、402 (欠费)、403 (禁用)

### 3. CircuitGuard — 熔断检查
- 与 RateLimitGuard 共享冷却机制
- 连续失败达到阈值后自动熔断

## 调度策略

### TASK_ROUTING 预排序
```
code      → anthropic > openai > deepseek
chat      → deepseek-cn > zhipu > openai > anthropic > deepseek > miclaw
cheap     → deepseek > dashscope > miclaw > local
vision    → openai > anthropic > google > dashscope
```

### 调度流程

```
┌─────────────────────────────────────────┐
│          call_with_fallback()           │
├─────────────────────────────────────────┤
│  1. pick_all(task)                      │
│     └─ filter_candidates()              │
│         ├─ QuotaGuard  ── 配额检查       │
│         ├─ RateLimitGuard ── 速率检查    │
│         └─ CircuitGuard ── 熔断检查      │
│                                         │
│  2. estimate_tokens(messages)           │
│  3. _filter_model() ── 能力过滤         │
│     ├─ context 窗口                     │
│     ├─ vision 支持                      │
│     └─ tool_use 支持                    │
│                                         │
│  4. 故障转移循环                         │
│     for pk in usable[:max_retries]:     │
│       ├─ 成功 → clear + record          │
│       └─ 失败 → cooldown + learn        │
│                                         │
│  5. 全部失败 → RuntimeError + 诊断报告    │
└─────────────────────────────────────────┘
```

## 与 Mother 的分工设计

TokenPool 的设计理念是 "Gateway 只知道 Key 可用/不可用，Mother 拥有最终选择权"：

- `pick_all()`：返回所有通过 GuardRail 的可用 Key（给 Gateway）
- `pick_with_scores()`：返回 Key + 评分详情（给 Mother 做最终选择）
- `pick()`：返回第一个可用 Key（简化版）

但实际上 Mother (mother_runtime.py) 没有使用 TokenPool 的调度结果，而是自己通过 `_build_candidates()` 直接遍历 pool.keys。

## 存在问题

1. **RateLimitGuard 和 CircuitGuard 检查同一个条件**：都是 `rl.is_on_cooldown()`
2. **调度结果未被 Mother 使用**：Mother 自己从 TokenPool 读 keys 自己做选择
3. **capability_score 未参与 caller 的 fallback 排序**：fallback 循环使用 TASK_ROUTING 预排序，未按评分动态排序
4. **filter_candidates 不做能力过滤**：能力过滤在 caller._filter_model 中单独做

## 建议

1. 合并 RateLimitGuard 和 CircuitGuard
2. 让 Mother 通过 TokenPool API 获取调度结果，而非直接读 keys
3. 在 pick_all 中集成能力过滤
4. 按评分排序候选列表

## 以后是否保留

**保留 GuardRail 设计**，但需与 Mother 统一调度入口。
