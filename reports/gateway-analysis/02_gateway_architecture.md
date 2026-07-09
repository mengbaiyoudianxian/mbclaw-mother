# 任务二：Gateway 架构分析

## 当前架构（三层）

```
┌─────────────────────────────────────────────────────┐
│                    通道层 (Adapters)                  │
│  QQBot  │  Wechat  │  Feishu  │  Web  │  CLI        │
│  WS     │  Poll    │  HTTP    │  HTTP  │  WS         │
└────────┬──────────┬──────────┬────────┬─────────────┘
         │          │          │        │
         ▼          ▼          ▼        ▼
┌─────────────────────────────────────────────────────┐
│                   逻辑层 (Gateway)                    │
│                                                     │
│  MessageNormalizer  →  StandardMessage              │
│  MessageRouter      →  route to Agent               │
│  ResponseDispatcher →  format + dispatch            │
│  GatewayRegistry    →  adapter management           │
└────────┬────────────────────────────────────────────┘
         │
         ├──→ MotherAgent.send()  (简单单轮) — 路径A
         │
         └──→ MotherRuntime.run() (完整多轮) — 路径B
              (通过 gateway_agent.py)
```

## 数据层

| 数据 | 存储 | 位置 |
|------|------|------|
| Message (对话) | messages 表 | SQLite |
| Session | sessions 表 | SQLite |
| User (设备码) | 心跳文件 + 隐含 | 文件系统 |
| Channel 状态 | 内存 | Adapter 实例 |
| Auth (admin) | admin_sessions.json | JSON |
| Transcript | session-{sid}.jsonl | 文件系统 |

## 逻辑层分析

| 模块 | 职责 | 质量 |
|------|------|:---:|
| `GatewayRegistry` | Adapter 注册/启动/停止 | ✅ 简洁 |
| `MessageNormalizer` | Channel → StandardMessage | ✅ 完整 (5 种) |
| `MessageRouter` | 路由到 MotherAgent | 🟡 绑定了旧的 MotherAgent.send() |
| `ResponseDispatcher` | 格式化 + 分发 | ✅ 完整 |
| `AdapterBase` | 抽象接口 | ✅ 清晰 |

## 安全层

| 安全机制 | 当前实现 | 问题 |
|---------|---------|------|
| Authentication | admin: sha256(password+salt) + session token | Gateway 无 auth |
| Permission | admin router: require_admin() | 设备端无验证 |
| Rate Limit | main.py middleware: simple 429 | 无 per-channel 限流 |
| CORS | allow_origins=["*"] | 过于宽松 |

## 调用关系（完整）

```
main.py (FastAPI lifespan)
    │
    ├── init_db()
    ├── GatewayRegistry
    │   ├── register('wechat', WechatAdapter)
    │   │   └── set_on_message(handle_gateway_agent)  ← 路径B
    │   └── wechat.start()  (长轮询)
    │
    ├── API Router (api_router)
    │   ├── POST /sessions     → create_session
    │   ├── POST /sessions/{sid}/messages → add_message
    │   ├── POST /sessions/{sid}/close    → close_session
    │   ├── GET  /search       → MemoryRepo.query()
    │   ├── POST /agent/run    → agent_run()  (路径C: 直接HTTP)
    │   └── GET  /tools        → list_tools()
    │
    └── Admin Router (admin_router)
        └── /admin/* → require_admin() → panel_one.html
```

## 三条调用路径并存问题

```
路径A: QQ/Feishu/Web/CLI → Normalizer → Router → MotherAgent.send()
       问题: MotherAgent.send() 是简单单轮, 不走 Memory/Context/Tools

路径B: WeChat → handle_gateway_agent() → MotherRuntime.run()
       问题: 绕过 Normalizer + Router + Dispatcher

路径C: HTTP POST /agent/run → agent_run()
       问题: 直接调 agent_run, 不经过 Gateway

→ 三条路径用三个不同的核心实现, 行为不一致
```
