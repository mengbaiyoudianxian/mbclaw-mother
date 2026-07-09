# 任务一：当前 TokenPool 盘点

> 精确盘点所有已存在/重复/缺失的能力

---

## 已存在的能力

### A. TokenPool 核心（token_pool.py，160 行）

| 能力 | 实现 | 位置 | 级别 |
|------|------|------|------|
| Key 加载 (心跳文件) | `_load()` 扫描 /var/lib/mbclaw/heartbeat_logs/*.json | L36-63 | 基础 |
| Key 加载 (MiClaw) | `_load()` 读取 miclaw_instances.json | L42-58 | 基础 |
| Key 模型 (PoolKey) | dataclass: code/api_key/base_url/model/provider/status/usage_count/last_used | L8-16 | 基础 |
| Key 状态缓存 | `_save()` → `/var/lib/mbclaw/token_pool.json` | L81-85 | 基础 |
| Key 测试 | `test_key()` HTTP POST /chat/completions "hi" 5 tokens | L87-105 | 基础 |
| Key 选择 (pick) | `pick()`: MiClaw 优先 → 用户 Key least-used | L110-138 | 简单 |
| 全局单例 | `get_pool()` | L151-155 | 基础 |
| LLMClient 集成 | `get_best_for_llm()` → (base_url, api_key, model) | L141-143 | 基础 |

### B. Provider 配置（models.py + providers.py）

| 能力 | 实现 | 位置 | 级别 |
|------|------|------|------|
| ModelProfile 表 | SQLAlchemy: key_alias/provider/model_name/api_base/api_key_env/priority/is_active | models.py L101-113 | 基础 |
| 默认 Provider Seeding | BUILTIN_PROVIDERS: openai-gpt4o/gpt4o-mini/local-ollama | providers.py L17-21 | 基础 |
| Provider 优先级 | `get_best_client()` 按 priority desc 排序 | providers.py L62-76 | 简单 |
| LLMClient TokenPool fallback | LLMClient.__init__() 无 key 时调 get_pool().get_best_for_llm() | llm.py L60-67 | 基础 |

### C. 管理面板统计

| 能力 | 实现 | 位置 | 级别 |
|------|------|------|------|
| 请求统计 | record_request() → total_requests/total_tokens_in/total_tokens_out/errors | admin/router.py L100-112 | 基础 |
| 每日统计 | daily: {date: {req, tin, tout}} | admin/router.py L109 | 基础 |
| 每 Provider 统计 | providers: {name: {req, tin, tout}} | admin/router.py L111-112 | 基础 |
| 设备在线统计 | heartbeat 扫描，10 分钟内在线数 | admin/router.py L170-185 | 基础 |
| Root/Key 统计 | root_count + key_ok_count | admin/router.py L190-195 | 简单 |

### D. MiClaw Bridge

| 能力 | 实现 | 位置 | 级别 |
|------|------|------|------|
| 实例管理 | apply/login/verify → miclaw_instances.json | bridge_manager.py | 独立系统 |
| 代理转发 | /bridge/miclaw/v1 → MiClaw 真实 API | bridge_manager.py | 独立系统 |
| 黑名单 | miclaw_blacklist.json | bridge_manager.py | 基础 |

---

## 重复的能力

| 能力 | 位置 1 | 位置 2 | 问题 |
|------|--------|--------|------|
| Provider 优先级 | providers.py `get_best_client()` | mother_runtime.py `_build_candidates()` | 两套优先级，不一致 |
| Key 选择 | token_pool.py `pick()` | mother_runtime.py `_build_candidates()` | 两套选择逻辑 |
| LLM Client 创建 | providers.py `get_best_client()` | llm.py `LLMClient.__init__()` | TokenPool fallback 重复 |
| Key 测试 | token_pool.py `test_key()` | FreeLLMAPI health check (如引入) | 需统一 |

---

## 缺失的能力

| 能力 | 说明 | 严重度 |
|------|------|--------|
| **Scoring** | 无 Key 评分 (latency/success rate/health score) | 🔴 高 |
| **Cooldown** | 失败的 Key 无冷却，下次立即重试 | 🔴 高 |
| **Circuit Breaker** | 无熔断，连续失败也不会停止使用 | 🔴 高 |
| **Rate Limit** | 无 RPM/TPM 限制，可能触发封号 | 🔴 高 |
| **429 处理** | 不识别 429 vs 5xx vs timeout | 🔴 高 |
| **Health Score** | 无健康评分，只有 working/failed 二元 | 🟡 中 |
| **Yesterday Usage** | 无昨日用量统计 | 🟡 中 |
| **每 Key 统计** | 无细粒度每 Key 指标 | 🟡 中 |
| **每 Model 统计** | 无模型维度用量 | 🟡 中 |
| **Budget 控制** | 无预算限额 | 🟡 中 |
| **用户 Token 贡献比** | 无 5%/10%/20% 配置 | 🟡 中 |
| **Key 隔离** | 无用户 Key 隔离 | 🟡 中 |
| **Round Robin** | pick() 是 least-used，不是 Round Robin | 🟢 低 |
| **Sticky Session** | 同一会话可能切换 Key | 🟢 低 |
| **Latency 记录** | 无延迟记录 | 🟢 低 |
| **Cost 计算** | 无费用估算 | 🟢 低 |

---

## TokenPool 当前调用关系

```
app/token_pool.py          ← TokenPool 自身（Key 存储 + 选择）
    ↑ 被调用
├── app/llm.py             ← LLMClient fallback
├── app/mother_runtime.py  ← _build_candidates() 遍历 pool.keys
└── app/admin/...          ← 仅统计展示

app/providers.py           ← ModelProfile（独立的 Provider 配置）
    ↑ 被调用
└── app/api.py             ← GET /providers

app/admin/bridge_manager.py ← MiClaw Bridge（独立系统）
```

**问题**: TokenPool 和 providers.py 是两套独立系统，没有互操作。
