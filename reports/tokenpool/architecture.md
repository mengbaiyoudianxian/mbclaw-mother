# TokenPool Architecture 分析

## 概述

TokenPool 是 LLM API Key 的统一管理与代理服务，端口 8100。功能包括：Key 注册/加密存储、多 Provider 支持、智能调度路由、速率限制、熔断、健康检测、MiClaw 桥接、用户共享 Key 管理和售出 Key 计费。

## 调用流程

```
请求来源 (Mother / 外部客户端)
    ↓
POST /v1/chat/completions (proxy.py)
    ↓
call_with_fallback() (caller.py)
    ↓
    ├── 1. Token 估算 (hybrid: rough + content-type correction)
    ├── 2. 图片/工具检测
    ├── 3. pick_all() → filter_candidates() (scheduler.py)
    │       ├── GuardRail 三层检查:
    │       │   ├── QuotaGuard: yesterday × share% = today_quota
    │       │   ├── RateLimitGuard: 滑动窗口 (RPM/RPD/TPM/TPD)
    │       │   └── CircuitGuard: 熔断冷却
    │       └── TASK_ROUTING 预排序
    ├── 4. _filter_model() (caller.py)
    │       ├── context 窗口检查
    │       ├── vision 能力检查
    │       └── tool_use 能力检查
    ├── 5. 故障转移循环 (最多 max_retries 个候选)
    │       ├── _call_openai_compat() 或 _call_anthropic()
    │       ├── 成功 → 记录 metrics + 清除冷却
    │       └── 失败 → 记录失败 + 设置冷却 + 自学习 limit
    └── 6. 返回 OpenAI 格式响应
```

## 模块架构

```
main.py (FastAPI 入口)
├── config.py (配置管理)
├── pool/
│   ├── registry.py     — Key + User 数据持久化 (SQLite, 加密存储)
│   ├── encryption.py    — AES-256-GCM 加密
│   ├── caller.py        — 统一调用器 + 故障转移
│   ├── scheduler.py     — GuardRail 编排 (Quota → RateLimit → Circuit)
│   ├── ratelimit.py     — 全维度速率限制 + 阶梯冷却 + 自学习
│   ├── scoring.py       — 综合评分 (Reliability + Speed + Capability)
│   ├── metrics.py       — 衰减加权指标聚合 (7天窗口, 2天半衰期)
│   ├── health.py        — 后台健康检测
│   ├── miclaw_pool.py   — MiClaw 账号池管理
│   ├── url_guard.py     — SSRF 防护
│   └── user_ratelimit.py — 每用户限流
├── routes/
│   ├── proxy.py         — /v1/chat/completions 代理
│   ├── keys.py          — Key CRUD
│   ├── stats.py         — 统计 API
│   ├── heartbeat.py     — 心跳接口
│   ├── admin.py         — 管理面板 (HTML)
│   ├── auth.py          — 认证
│   ├── user_stats.py    — 用户共享Key管理 + MiClaw账号管理
│   ├── miclaw_login.py  — MiClaw 登录路由
│   ├── free_keys.py     — 免费营销 Key
│   └── sold_keys.py     — 售出 Key 管理与计费
└── requirements.txt
```

## 数据库表 (SQLite)

| 表名 | 用途 |
|------|------|
| keys | Provider Key 配置 (管理员) |
| key_stats | Key 运行时统计 |
| users | 用户认证 |
| user_shared_keys | 用户心跳贡献的共享 Key |
| miclaw_accounts | MiClaw 账号池 |
| free_shared_keys | 免费营销 Key |
| sold_keys | 售出 Key |
| sold_key_models | 售出 Key 模型倍率 |
| sold_key_usage | 售出 Key 用量记录 |
| call_log | 调用日志 |
| ratelimit.db (独立) | 速率限制冷却状态 |

## 存在问题

1. **两套限流器并存**：ratelimit.py (Key级) 和 user_ratelimit.py (用户级) 各自独立
2. **评分系统未充分用于调度**：scoring.py 的评分结果主要用于展示，caller.py 的 fallback 主要依赖顺序遍历
3. **caller.py 与 Mother token_pool.py 功能重叠**：两者都做了 Key 测试和选择
4. **MML (capability profile) 只覆盖少数模型**：大量模型无画像
5. **SSRF 防护（url_guard.py）未被 routes 使用**：sold_keys 等路由直接写 base_url 无校验

## 建议

1. 合并 ratelimit.py 和 user_ratelimit.py 为统一限流框架
2. 在 caller.py 中引入评分驱动的选择策略（而不只是顺序遍历）
3. Mother 应通过 TokenPool API 调用，而非直接读心跳文件
4. 所有写 URL 的 API 都应启用 url_guard 校验
