# TokenPool Router 分析

## 作用

Router 层负责 Key 的智能选择和调度，通过三层 GuardRail（Quota → RateLimit → Circuit）过滤不可用 Key，再按 TASK_ROUTING 偏好排序。

## Scheduler (scheduler.py)

### GuardRail 三层检查

```
filter_candidates()
    ↓
for each enabled key:
    ├── QuotaGuard.check(pk)
    │   └── 仅用户共享Key: yesterday_usage × share% = today_quota
    │       今天已用量 >= 配额 → 拒绝
    ├── RateLimitGuard.check(pk)
    │   └── is_on_cooldown? → 拒绝
    └── CircuitGuard.check(pk)
        └── is_on_cooldown? → 拒绝 (与RateLimit共用冷却机制)
    ↓
TASK_ROUTING 预排序
```

### TASK_ROUTING 偏好

| 任务 | 偏好 Provider 顺序 |
|------|-------------------|
| code | anthropic, openai, deepseek |
| reasoning | anthropic, openai, deepseek |
| chat | deepseek-cn, zhipu, openai, anthropic, deepseek, miclaw |
| cheap | deepseek, dashscope, miclaw, local |
| vision | openai, anthropic, google, dashscope |

### 接口设计

- **Gateway 用**：`pick_all()` → 返回可用 Key 列表（不做最终选择）
- **Mother 用**：`pick_with_scores()` → 返回 Key + 评分详情（Mother 自己做最终决策）
- **简化版**：`pick()` → 返回第一个可用 Key

## Ratelimit (ratelimit.py)

### 全维度速率限制
- **4 轴滑动窗口**：RPM、RPD、TPM、TPD（每分钟/每日 请求数/Token数）
- **阶梯冷却**：连续撞墙 1→4 次，冷却时间 2min → 10min → 1hr → 24hr
- **按状态码冷却**：429 transient (90s)、402 payment (24h)、403 forbidden (24h)
- **自学习**：解析上游 429 错误 body 中的真实 limit，自动更新
- **Provider 级日上限**：如 OpenRouter 1000次/天
- **持久化**：SQLite rate_limit.db 保存冷却状态

### 冷却计算逻辑
```
HTTP 429 → _determine_cooldown(429)
    ├── 24h内第1次: 2分钟
    ├── 24h内第2次: 10分钟
    ├── 24h内第3次: 1小时
    └── 24h内第4+: 24小时
HTTP 402 → 24小时
HTTP 403 → 24小时
```

## Scoring (scoring.py)

### 综合评分公式
```
score = w_rel × reliability + w_spd × speed + w_cap × capability
```

### 四策略权重
| 策略 | reliability | speed | capability |
|------|------------|-------|------------|
| balanced | 0.5 | 0.25 | 0.25 |
| smartest | 0.35 | 0.1 | 0.55 |
| fastest | 0.35 | 0.55 | 0.1 |
| reliable | 0.7 | 0.15 | 0.15 |

### 三维度分项
- **Reliability**：Beta(α,β) 后验期望，无数据时 0.5
- **Speed**：0.5×ttfb_score + 0.5×tokps_score（或降级为 latency）
- **Capability**：内置模型画像匹配度，无画像时 0.5

### 模型画像（BUILTIN_CAPABILITIES）
覆盖 ~30 个模型，包含 context 窗口、vision 支持、tool_use 支持、各任务评分等。

## 存在问题

1. **RateLimitGuard 和 CircuitGuard 检查同一个冷却状态**：实际上两层都是 is_on_cooldown 检查
2. **QuotaGuard 只检查用户共享 Key**：管理员配置的 Key 不受限
3. **评分结果主要用于展示**：caller.py 的 fallback 循环按顺序遍历，未按评分排序
4. **TASK_ROUTING 的 provider 列表硬编码**：新增 provider 需改代码
5. **scoring.py 与 caller.py 的 _filter_model 重复了能力检查**：一个是评分维度的 capability_score()，一个是硬性过滤

## 以后是否保留

- **scheduler.py**：保留 GuardRail 设计，但 RateLimitGuard 和 CircuitGuard 应合并
- **ratelimit.py**：保留，与 user_ratelimit.py 合并
- **scoring.py**：保留，但评分应真正用于调度决策
