# TokenPool Metrics 分析

## 作用

Metrics 层提供衰减加权指标聚合，支持 7 天窗口 + 2 天半衰期的数据统计，用于评分系统和实时监控。

## MetricsHub (metrics.py)

### 衰减加权机制
- **窗口**：7 天
- **半衰期**：2 天
- **衰减公式**：weight = 0.5 ^ (age_ms / HALF_LIFE_MS)
- **含义**：2 天前的数据加权后仍有 50% 影响力

### 核心指标 (AliasMetrics)
| 指标 | 计算方式 |
|------|---------|
| success_rate | 衰减加权成功率 [0, 1] |
| avg_latency | 衰减加权平均延迟 (仅成功调用) |
| total_tokens | 衰减加权累计 Token |
| total_cost | 衰减加权累计成本 |
| rpm | 5 分钟滑动窗口 RPM (不用衰减) |
| raw_count | 7 天窗口内原始请求数 |
| samples_7d | 同 raw_count |

### MetricsTracker (scoring.py 内的独立 tracker)
- 滑动窗口最近 100 次调用记录
- 按 streaming=True/False 分别计算 TTFB + tok/s
- 无流式数据时降级为 TTFB + latency

### 指标快照示例
```json
{
  "alias": "openai-gpt4o",
  "success_rate": 0.985,
  "avg_latency_ms": 1234.5,
  "total_tokens_7d": 1250000,
  "total_cost_7d": 6.25,
  "rpm": 3.2,
  "samples_7d": 852,
  "half_life_days": 2
}
```

## 数据流

```
call_with_fallback() (caller.py)
    ↓
每次调用后:
    ├── hub.record(alias, latency, tokens, cost, success)    → MetricsHub
    ├── tracker.record(alias, ttfb, latency, out_tokens, ...) → MetricsTracker
    └── reg.update_stat(...)                                  → Registry (key_stats 表)
```

## 存在问题

1. **三套统计并存**：MetricsHub (衰减加权)、MetricsTracker (滑动窗口)、Registry.key_stats (累计值) 各自独立
2. **MetricsHub 内存存储，重启清零**：衰减加权数据不持久化
3. **MetricsTracker 的输入数据来自 caller 估算**：非流式场景下 ttfb 和 tok/s 是估算值
4. **RPM 是 5 分钟窗口**：与 ratelimit 的 1 分钟 RPM 窗口不一致

## 建议

1. 合并 MetricsHub 和 MetricsTracker 为统一指标层
2. 关键指标应持久化（至少最近 24h）
3. 统一 RPM 窗口大小

## 以后是否保留

**保留设计思路**，衰减加权比简单平均值更合理。但需与 Ratelimit 的统计统一。
