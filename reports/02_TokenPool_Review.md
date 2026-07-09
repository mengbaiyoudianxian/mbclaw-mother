# 02 — TokenPool 架构评审

> 评审人：MBclaw 高级架构师
> 日期：2026-07-09
> 状态：Phase 0 Architecture Freeze（只读分析）

---

## 一、工程概况

TokenPool 是一个独立的 FastAPI 服务（端口 8100），负责 LLM API Key 的统一管理、调度和代理转发。设计目标为「商业化中转站」。

### 文件统计

```
tokenpool/ 共 21 个源文件
├── pool/      12 个模块 (核心引擎)
├── routes/    11 个路由 (API 层)
├── main.py    入口
├── config.py  配置
└── requirements.txt
```

---

## 二、Provider 生命周期

```
┌─────────────────────────────────────────────────────────┐
│                  Provider Key 生命周期                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. 注册                                                │
│     ├── 内置: BUILTIN 7 个 Key (openai/anthropic/...)   │
│     ├── 手动: POST /api/keys                            │
│     ├── 心跳: heartbeat_logs → user_shared_keys         │
│     └── MiClaw: miclaw_accounts 表                      │
│                                                         │
│  2. 加密存储                                             │
│     └── AES-256-GCM → encrypted_key + key_iv + key_tag  │
│                                                         │
│  3. 健康检测                                             │
│     ├── 定时: health.check_all() 每 300s                 │
│     ├── 实时: call_with_fallback 每次调用更新状态         │
│     └── 用户Key: _probe_user_keys() 每 1h                │
│                                                         │
│  4. 运行时状态                                           │
│     ├── working  → 正常服务                              │
│     ├── failed   → 调用/检测失败                         │
│     ├── unknown  → 未测试                               │
│     └── cooldown → 熔断冷却中                            │
│                                                         │
│  5. 淘汰                                                 │
│     └── 手动禁用 (enabled=False) 或心跳超时              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Key 类型分类

| 类型 | 表 | 来源 | 特点 |
|------|-----|------|------|
| 管理员 Key | keys | 内置 + 手动 | 全权限，无限额 |
| 用户共享 Key | user_shared_keys | 心跳自动收集 | 共享比例控制 |
| MiClaw 账号 | miclaw_accounts | 手动 + Bridge 登录 | 归属+借用白名单 |
| 免费 Key | free_shared_keys | 设备注册发放 | 总量/日/速率限制 |
| 售出 Key | sold_keys | 手动添加 | 倍率+余额计费 |

---

## 三、Scheduler 调度流程

### GuardRail 三层检查

```
filter_candidates(require_model, require_apikey)
    │
    for each enabled key:
    │
    ├── QuotaGuard.check(pk)
    │   └── 仅 user_shared_keys:
    │       yesterday_usage × share_percent = today_quota
    │       今日已用 >= 配额 → REJECT
    │
    ├── RateLimitGuard.check(pk)
    │   └── is_on_cooldown(pk)?
    │       是 → REJECT (冷却中)
    │
    └── CircuitGuard.check(pk)
        └── is_on_cooldown(pk)?
            是 → REJECT (熔断中)
    │
    ▼
TASK_ROUTING 预排序
    code      → anthropic > openai > deepseek
    chat      → deepseek-cn > zhipu > openai > anthropic > deepseek > miclaw
    cheap     → deepseek > dashscope > miclaw > local
    vision    → openai > anthropic > google > dashscope
```

### 与 Mother 的分工设计

```
Gateway (TokenPool):  pick_all() → 返回可用 Key 列表 (不做选择)
Mother:               pick_with_scores() → Key + 评分详情 (Mother 做最终决策)
```

**但实际上 Mother 从未使用这些 API。**

---

## 四、Router 工作流程 (Caller)

```
POST /v1/chat/completions (proxy.py)
    │
    ▼
call_with_fallback(payload, task, budget, require_model, max_retries=3)
    │
    ├── 1. pick_all(task) — GuardRail 过滤
    │
    ├── 2. estimate_tokens(messages, max_out)
    │       ├── rough = len(json) // 4
    │       ├── _detect_content_type() → chinese(1.3x) / code(1.5x) / english(1.0x)
    │       └── estimated = rough × factor + max_out
    │
    ├── 3. _filter_model() — 能力过滤
    │       ├── context 窗口: estimated > cap.context → SKIP
    │       ├── vision: has_images and cap.vision <= 0 → SKIP
    │       └── tool_use: has_tools and cap.tool_use <= 0 → SKIP
    │
    ├── 4. 故障转移循环 (最多 max_retries 个候选)
    │       for pk in usable[:max_retries]:
    │           ├── anthropic → _call_anthropic()
    │           ├── 其他 → _call_openai_compat()
    │           │
    │           ├── 成功:
    │           │   ├── rl.clear_cooldown()
    │           │   ├── hub.record() + tracker.record()
    │           │   ├── reg.update_stat("working")
    │           │   └── return (response, alias)
    │           │
    │           └── 失败:
    │               ├── rl.set_cooldown(status_code)
    │               ├── rl.learn_from_error()
    │               ├── reg.update_stat("failed")
    │               └── continue (下一个候选)
    │
    └── 5. 全部失败 → RuntimeError + 诊断报告
```

---

## 五、Metrics 收集流程

### 三套统计系统

```
call_with_fallback() 每次调用后:
    │
    ├── hub.record(alias, latency, tokens, cost, success)
    │   └── MetricsHub (衰减加权, 7天窗口, 2天半衰期)
    │       内存存储, 重启清零
    │
    ├── tracker.record(alias, ttfb, latency, out_tokens, success, streaming)
    │   └── MetricsTracker (滑动窗口 100 条, TTFB+tokens/s)
    │       内存存储, 重启清零
    │
    └── reg.update_stat(alias, status, latency, tokens, cost, success)
        └── Registry.key_stats 表 (累计值)
            持久化到 SQLite
```

### 评分系统

```
综合评分 = w_rel × reliability + w_spd × speed + w_cap × capability

四策略:
  balanced:  0.50 / 0.25 / 0.25
  smartest:  0.35 / 0.10 / 0.55
  fastest:   0.35 / 0.55 / 0.10
  reliable:  0.70 / 0.15 / 0.15

reliability: Beta(α,β) 后验期望 [0,1]
speed:       0.5×ttfb_score + 0.5×tokps_score (或降级 latency)
capability:  模型画像匹配度 (BUILTIN_CAPABILITIES, ~30 模型)
```

**关键问题：评分结果主要用于展示面板，caller 的故障转移未按评分排序。**

---

## 六、熔断流程 (Ratelimit)

```
HTTP 429 响应:
    │
    ├── 阶梯冷却:
    │   24h内第1次 → 2分钟
    │   24h内第2次 → 10分钟
    │   24h内第3次 → 1小时
    │   24h内第4次 → 24小时
    │
    ├── 自学习: 解析上游 error body 中的真实 limit
    │   自动更新 rpm_limit / tpm_limit
    │
    └── 持久化: ratelimit.db 保存冷却状态

HTTP 402 → 24小时冷却
HTTP 403 → 24小时冷却
```

### 速率限制维度

| 维度 | 窗口 | 说明 |
|------|------|------|
| RPM | 1 分钟 | 请求数 |
| RPD | 1 天 | 请求数 |
| TPM | 1 分钟 | Token 数 |
| TPD | 1 天 | Token 数 |
| Provider日上限 | 1 天 | 如 OpenRouter 1000次/天 |

---

## 七、API 生命周期

### 路由分组

| 前缀 | 文件 | 功能 |
|------|------|------|
| /v1/chat/completions | proxy.py | LLM 代理 (核心) |
| /api/keys | keys.py | Key CRUD |
| /api/stats | stats.py | 统计查询 |
| /api/heartbeat | heartbeat.py | 心跳上报 |
| /api/admin | admin.py | 管理面板 + API |
| /api/auth | auth.py | 认证 |
| /api/shared-keys | user_stats.py | 用户共享Key + MiClaw |
| /api/free-keys | free_keys.py | 免费Key |
| /api/sold-keys | sold_keys.py | 售出Key |
| /api/miclaw | miclaw_login.py | MiClaw 登录 |

---

## 八、数据库存储

### 两套 SQLite

```
pool.db (主库):
├── keys                  # 管理员 Key 配置
├── key_stats             # Key 运行时统计
├── users                 # 用户认证
├── user_shared_keys      # 用户共享 Key
├── miclaw_accounts       # MiClaw 账号池
├── free_shared_keys      # 免费 Key
├── sold_keys             # 售出 Key
├── sold_key_models       # 模型倍率
├── sold_key_usage        # 用量记录
└── call_log              # 调用日志

ratelimit.db (独立):
├── cooldowns             # 冷却状态
└── learned_limits        # 自学习限制
```

---

## 九、商业化适合度评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 多 Key 管理 | ⭐⭐⭐⭐ | 5 种 Key 类型，加密存储 |
| 调度能力 | ⭐⭐⭐⭐ | GuardRail + 故障转移 + 评分 |
| 计费能力 | ⭐⭐⭐ | sold_keys 有倍率+余额，但无支付集成 |
| 速率限制 | ⭐⭐⭐⭐ | 4 轴滑动窗口 + 阶梯冷却 |
| 安全性 | ⭐⭐⭐ | AES 加密 + SSRF 防护，但 API 鉴权简单 |
| 可观测性 | ⭐⭐⭐ | 三套统计但各自独立，无告警 |
| 高可用 | ⭐⭐ | 单实例，无主备 |

### 商业化风险

| 风险 | 等级 | 说明 |
|------|------|------|
| Mother 不用 TokenPool | 🔴 致命 | Mother 内置了 Key 管理副本，绕过所有商业化控制 |
| 评分未用于调度 | 🟡 高 | 故障转移顺序遍历，不按评分择优 |
| 两套限流器并存 | 🟡 中 | ratelimit + user_ratelimit 未统一 |
| 无支付集成 | 🟡 中 | sold_keys 有余额字段但无可充值接口 |
| 单实例部署 | 🟡 中 | 无主备切换，无负载均衡 |
| 指标不持久化 | 🟢 低 | MetricsHub/Tracker 重启清零 |

---

## 十、架构评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 设计完整性 | ⭐⭐⭐⭐ | GuardRail + Scheduler + Caller 层次清晰 |
| 代码质量 | ⭐⭐⭐⭐ | 模块划分合理，比 Mother 干净 |
| 功能完备性 | ⭐⭐⭐⭐ | Key 管理、调度、限流、计费都有 |
| 实际使用率 | ⭐⭐ | Mother 绕过它，商业化功能闲置 |

### 核心问题

TokenPool 是一个**设计良好但未被正确使用的服务**。Mother 绕过它的 HTTP API，
直接读文件系统获取 Key，导致 TokenPool 的 Scheduler、GuardRail、熔断、评分
全部被旁路。商业化计费功能也因缺乏实际流量而闲置。
