# 任务四：Provider 设计

> 包含 Provider、ProviderKey、Endpoint、Capability、Health、Metrics、Budget、RateLimit、Cooldown 的完整设计

---

## Provider 数据模型

### Provider
```
Provider:
    id: int (PK)
    name: str              "openai" / "zhipu" / "deepseek" / "miclaw-bridge" / "freellmapi"
    display_name: str      "OpenAI" / "智谱" / "DeepSeek"
    provider_type: enum    commercial / free_proxy / user_contributed / admin_private
    priority: int          越小越优先 (0=最高)
    enabled: bool
    description: str
    created_at: datetime
```

### ProviderKey
```
ProviderKey:
    id: int (PK)
    provider_id: int (FK → Provider)
    key_alias: str         管理员可见名称
    api_key: str           API Key (明文存储，MBclaw 是单实例本地)
    base_url: str          API Base URL
    model: str             模型名
    key_type: enum         commercial / user_contributed / admin_private / free_proxy
    contribution_ratio: float    用户贡献比 (0.05=5%, 0.10=10%, 0.20=20%)
    owner_code: str        贡献者设备码 (user_contributed 时)
    status: enum           healthy / degraded / error / unknown / disabled
    health_score: float    0.0 ~ 1.0 (综合: latency + success_rate + error_rate)
    tested_at: datetime    最后健康检查时间
    consecutive_errors: int     连续错误次数 (≥3 → disabled)
    penalty: int          429 惩罚分 (0-10)
    usage_count: int      累计使用次数
    last_used_at: datetime
    rpm_limit: int        Request Per Minute (0=不限)
    tpm_limit: int        Token Per Minute (0=不限)
    daily_token_limit: int      每日 Token 限额
    monthly_budget: float       月度预算 (USD)
    enabled: bool
    created_at: datetime
```

### ProviderEndpoint
```
ProviderEndpoint:
    id: int (PK)
    provider_id: int (FK → Provider)
    path: str             "/chat/completions" / "/models" / "/embeddings"
    method: str           GET / POST
    is_chat_endpoint: bool     是否聊天端点
    enabled: bool
```

### KeyMetrics
```
KeyMetrics:
    id: int (PK)
    key_id: int (FK → ProviderKey)
    date: date            统计日期
    request_count: int    请求数
    token_in: int        输入 Token
    token_out: int       输出 Token
    avg_latency_ms: float      平均延迟
    error_count: int     错误数
    rate_limit_count: int      429 次数
    created_at: datetime
```

---

## Provider 类型分类

| 类型 | 来源 | 策略 | 示例 |
|------|------|------|------|
| commercial | 管理员购买 | 付费优先，严格限流 | OpenAI API Key |
| admin_private | 管理员私有 | 最高优先级，不共享 | 管理员自己的 Key |
| user_contributed | 用户心跳上报 | 按贡献比授权，自动熔断 | 用户手机上的 Key |
| free_proxy | 免费代理 | 低优先级，fallback 用 | MiClaw Bridge, FreeLLMAPI |

---

## Provider Health 评分算法

```
health_score = (
    latency_score * 0.3 +
    success_rate * 0.5 +
    penalty_decay * 0.2
)

latency_score:
  < 500ms  → 1.0
  < 2000ms → 0.7
  < 5000ms → 0.3
  ≥ 5000ms → 0.0

success_rate:
  最近 10 次成功 / 10

penalty_decay:
  1.0 - (penalty / 10)
```

## ProviderKey 选择流程

```
Scheduler 请求: (preferred_provider, estimated_tokens, session_id)

1. Filter: enabled=True, status in (healthy, degraded, unknown)
2. Sticky: if session has preferred → move to front
3. Sort: provider.priority ASC + key.penalty ASC + key.health_score DESC
4. Rate Limit: can_proceed(key, estimated_tokens)
5. Round-Robin: 同优先级的 key 轮询
6. Return: (base_url, api_key, model)
```

---

## 当前 Provider 映射

| 当前 (160行) | 新设计 | 说明 |
|-------------|--------|------|
| `PoolKey.dataclass` | `ProviderKey` ORM | 纯内存 → 持久化 |
| `HEARTBEAT_DIR` 扫描 | `ProviderKey` 表 | 文件系统 → DB |
| `miclaw_instances.json` | `Provider(provider_type=free_proxy)` | 独立文件 → 统一表 |
| `providers.py BUILTIN_PROVIDERS` | `Provider` 种子数据 | 硬编码 → DB |
| `providers.py ModelProfile` | `Provider` 表 | 合并 |
| `token_pool.json` 缓存 | `KeyMetrics` 表 | 分散 → 统一 |
