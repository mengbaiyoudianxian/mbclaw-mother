# 04 — MBclaw 整体架构评审

> 评审人：MBclaw 高级架构师
> 日期：2026-07-09
> 状态：Phase 0 Architecture Freeze（只读分析）

---

## 一、工程全景

### 部署拓扑

```
┌──────────────────────────────────────────────────────────────┐
│                      用户入口                                 │
│         Android App  │  QQ  │  微信  │  Web                  │
└──────┬──────────┬──────┬──────┴──────┬──┴────────────────────┘
       │          │      │             │
       │ 心跳     │ QQ消息│ 微信消息    │ Web聊天
       ▼          ▼      ▼             ▼
┌──────────────────────────────────────────────────────────────┐
│              Mother (母体) — 端口 80                          │
│              FastAPI 单进程                                   │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  MotherRuntime  │  Gateway   │  Control Panel        │    │
│  │  (Agent Loop)   │  (多渠道)  │  (管理面板)           │    │
│  └────────┬────────┴─────┬──────┴──────┬────────────────┘    │
│           │              │             │                      │
│           │  SQLite DB   │  JSON Files │  内置 TokenPool 副本  │
│           │  (mbclaw.db) │  (10+ 文件) │  (app/token_pool.py) │
│           │              │             │                      │
│           │              │             │ 读 heartbeat_logs/    │
│           │              │             │ 直接选 Key            │
└───────────┼──────────────┼─────────────┼──────────────────────┘
            │              │             │
            │              │             │ HTTP (仅 Key 测试)
            ▼              ▼             ▼
┌──────────────────────────────────────────────────────────────┐
│            TokenPool (工具池) — 端口 8100                      │
│            FastAPI 独立进程                                    │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Registry │  │ Scheduler │  │  Caller  │  │Health/Metr │  │
│  │ (Key管理)│  │(GuardRail)│  │(故障转移)│  │(健康/指标) │  │
│  └──────────┘  └───────────┘  └──────────┘  └────────────┘  │
│                                                                │
│  SQLite: pool.db + ratelimit.db                                │
└──────────────────────────────┬─────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│              MiClaw Bridge — 端口 8765                         │
│              (第三方服务，非 MBclaw 自研)                       │
└──────────────────────────────┬─────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│              上游 LLM Provider                                 │
│  OpenAI │ Anthropic │ DeepSeek │ 智谱 │ 通义千问 │ ...        │
└──────────────────────────────────────────────────────────────┘
```

### 关键数据流

```
设备心跳:
  App → POST /admin/client/debug/heartbeat → heartbeat_logs/mb-{code}.json
         ├── Mother (token_pool.py) 读取 → 获取 Key
         ├── Control Panel 读取 → 显示设备列表
         └── TokenPool (/api/heartbeat) 接收 → user_shared_keys 表

LLM 调用 (当前实际):
  MotherRuntime._build_candidates()
    → app.token_pool.get_pool().keys  (读 heartbeat_logs)
    → httpx.post(LLM)  (直接调用，绕过 TokenPool)

LLM 调用 (应有但未用的路径):
  Mother → POST http://tokenpool:8100/v1/chat/completions
    → TokenPool Scheduler → GuardRail → Caller → LLM

管理面板数据:
  Dashboard → stats.json (Mother 的 API 中间件写入)
  设备列表 → heartbeat_logs/* (debug_api_v2 写入)
  Token 池 → heartbeat_logs/* (不是 TokenPool 数据库!)
  MiClaw   → miclaw_instances.json
```

---

## 二、三工程调用关系图

```
                    ┌──────────────────────┐
                    │    Control Panel     │
                    │  (Mother 进程内)     │
                    └──┬──────┬──────┬─────┘
                       │      │      │
          进程内调用    │      │      │ HTTP (硬编码 IP)
          共享文件      │      │      │
                       ▼      │      ▼
              ┌───────────┐  │  ┌──────────────┐
              │  Mother   │◄─┘  │  TokenPool   │
              │  Runtime  │     │  服务 :8100   │
              └─────┬─────┘     └──────┬────────┘
                    │                  │
         ┌─────────┼─────────┐        │
         ▼         ▼         ▼        │
    ┌────────┐┌────────┐┌────────┐    │
    │heartbeat││ SQLite ││  JSON  │    │
    │_logs/  ││  DB   ││  Files │    │
    └────────┘└────────┘└────────┘    │
         ▲         ▲                  │
         └─────────┼──────────────────┘
                   │
          文件系统共享 (同一台机器)
```

### 调用关系详解

```
1. Mother → TokenPool: 文件系统（读 heartbeat_logs） ❌ 不应如此
   Mother → TokenPool: HTTP API                        ✅ 应有但未用

2. Control Panel → Mother: 进程内（同一 FastAPI app）
   Control Panel → Mother: 共享 DB/文件

3. TokenPool → Mother: 无通知机制
   TokenPool → Mother: 文件系统（写 pool.db）          ❌ Mother 不读 pool.db

4. Mother → Control Panel: 无通知机制
   Mother → Control Panel: 共享文件（stats.json）      ✅ 前端轮询

5. Control Panel → TokenPool: HTTP API (仅 Key 测试)   ⚠️ 部分使用
   Control Panel → TokenPool: 文件系统（读 heartbeat） ❌ Token 列表绕过 API
```

---

## 三、已存在的 API

### Mother 核心 API (api.py)

```
POST   /sessions                    # 创建会话
POST   /sessions/{sid}/messages     # 添加消息
POST   /sessions/{sid}/close        # 关闭会话(摘要→记忆)
GET    /sessions/{sid}/messages     # 消息列表
GET    /search?q=                   # 搜索记忆
POST   /agent/run                   # Agent Loop
GET    /agent/status                # Agent 状态
GET    /tools                       # 工具列表
POST   /tools/execute               # 执行工具
GET    /providers                   # Provider 列表
GET    /client/version              # 客户端版本
```

### Control Panel API (admin/)

```
POST   /admin/api/login             # 管理登录
POST   /admin/api/logout            # 管理登出
POST   /admin/api/change-password   # 修改密码
GET    /admin/api/overview          # 总览统计
GET    /admin/api/users             # 用户列表
GET    /admin/api/token-pool        # Token 池(读文件)
POST   /admin/api/token-pool/test-key    # Key 测试(调TokenPool)
POST   /admin/api/token-pool/test-all    # 全量检测(调TokenPool)
GET    /api/admin/metrics            # 服务器指标
GET    /admin/client/debug/devices   # 设备列表
POST   /admin/client/debug/send     # 下发命令
POST   /admin/client/debug/heartbeat # 心跳
ANY    /bridge/miclaw/*             # MiClaw 桥接
GET    /admin/client/version        # 版本检测
```

### TokenPool API (routes/)

```
POST   /v1/chat/completions         # LLM 代理 (核心)
GET    /api/keys                    # Key 列表
POST   /api/keys                    # 添加 Key
GET    /api/stats                   # 统计
POST   /api/heartbeat               # 心跳
POST   /api/shared-keys/probe-all   # 全量检测
POST   /api/shared-keys/legacy/test-key # Key 测试
GET    /api/shared-keys/legacy/tokens   # Token 列表
... (共 ~30 个端点)
```

---

## 四、重复分析

### API 功能重复

| 功能 | Mother 实现 | TokenPool 实现 | Panel 实现 | 建议 |
|------|-----------|---------------|-----------|------|
| Token/Key 列表 | token_pool.py (读文件) | GET /api/keys (查DB) | 读 heartbeat_logs | 统一到 TokenPool API |
| Key 测试 | TokenPool.test_key() | POST /probe | 调 TokenPool | 保留 TokenPool |
| LLM 调用 | 4 条路径 | call_with_fallback() | - | 统一到 TokenPool /v1/chat/completions |
| 设备管理 | debug_api_v2.py | - | 读 heartbeat_logs | 保留 Mother |
| 统计 | stats.json | call_log 表 | stats.json | 统一到 TokenPool |

### 代码模块重复

| 功能 | 重复位置 |
|------|---------|
| Agent Loop | mother_runtime.py + agent.py |
| LLM 客户端 | llm.py + llm_router.py |
| Tool 运行时 | tools.py + tool_runtime.py |
| TokenPool 客户端 | app/token_pool.py + admin/router.py (_tp_req) |
| 系统监控 | mbos_core.py + admin_api.py (_read_network_bytes) |

---

## 五、数据存储全景

```
┌─────────────────────────────────────────────────────────────┐
│                    数据存储全景                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Mother SQLite (mbclaw.db):                                 │
│    sessions, messages, summaries, keywords, experiences     │
│    tools, model_profiles                                    │
│    + FTS5: messages_fts, experiences_fts                    │
│                                                             │
│  TokenPool SQLite (pool.db):                                │
│    keys, key_stats, users, user_shared_keys                 │
│    miclaw_accounts, free_shared_keys                        │
│    sold_keys, sold_key_models, sold_key_usage               │
│    call_log                                                 │
│                                                             │
│  TokenPool SQLite (ratelimit.db):                            │
│    cooldowns, learned_limits                                │
│                                                             │
│  Control Panel JSON (10+ 文件):                              │
│    admin.json, admin_sessions.json                           │
│    users.json, stats.json, keys.json                         │
│    miclaw_instances.json, miclaw_blacklist.json              │
│    bugs.json, features.json, version.json                   │
│    downloads.json, accounts.json, shared_tools.json         │
│    server_status.json, pending_commands.json                │
│                                                             │
│  Heartbeat (按设备):                                         │
│    heartbeat_logs/mb-{code}.json (每设备 1 个)              │
│                                                             │
│  总计: 3 个 SQLite + 10+ JSON 文件 + N 个 heartbeat 文件     │
│  问题: 数据分散，无统一数据源，无事务一致性                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 六、架构评分总结

| 维度 | Mother | TokenPool | Panel | 整体 |
|------|--------|-----------|-------|------|
| 功能完整性 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 代码整洁度 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| 模块边界 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| 数据架构 | ⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐ |
| 安全性 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| 可维护性 | ⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐ |
| **综合** | **2.5** | **3.3** | **1.8** | **2.7** |

### 三句话总结

1. **Mother 功能完整但代码混乱**：4 条 LLM 路径、3 套工具系统、内置 TokenPool 副本绕过独立服务
2. **TokenPool 设计最好但未被正确使用**：Mother 绕过它的 HTTP API，商业化功能闲置
3. **Control Panel 功能最全但架构最差**：10+ JSON 文件、前端单文件、数据源分散

### 最大的架构问题

**Mother 和 TokenPool 之间没有真正的服务边界。** Mother 通过读文件系统
来「调用」TokenPool，使得 TokenPool 的 GuardRail、熔断、限流、评分、计费
全部被绕过。TokenPool 实际上是一个「影子服务」——存在但不起作用。
