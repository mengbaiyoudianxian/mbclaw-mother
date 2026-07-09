# 任务四：OpenHands Gateway

## 请求生命周期

```
User Browser / API Client
    │
    ▼
FastAPI Server (openhands/server/)
    │── CORS Middleware
    │── Auth Middleware (session/JWT)
    │
    ▼
API Router (/api/conversations)
    │── POST /conversations → create conversation
    │── POST /conversations/{id}/messages → send message
    │── GET  /conversations/{id} → get status
    │
    ▼
Conversation Manager
    │── create/load Conversation
    │── bind Agent (SDK)
    │── forward message → SDK Agent
    │
    ▼
SDK Agent (openhands-sdk)
    │── Agent Loop (planner → executor → observer)
    │── Condenser (context compression)
    │── Tools (bash/browser/editor)
    │
    ▼
Response → Conversation Manager → API Response → User
```

## 哪些属于 Gateway

| OpenHands 层 | 对应 MBclaw | 归属 |
|-------------|-----------|------|
| FastAPI Server | main.py | Gateway |
| Auth Middleware | admin/router.py _check_session | Gateway |
| CORS Middleware | main.py CORS | Gateway |
| API Router (/conversations) | api.py router | Gateway |
| Conversation Manager | Session 管理 | Gateway ↔ Runtime |
| SDK Agent | MotherRuntime | Runtime |

## 哪些属于 Memory / Session / Context

| OpenHands 数据 | 归属 | MBclaw 对应 |
|---------------|------|-----------|
| Conversation messages | Session | messages 表 |
| Conversation status | Session | sessions.status |
| Condenser output | Context | WorkingMemory 压缩结果 |
| Agent state | Session | Session 内存状态 |
| User settings | Memory | user_profiles (远期) |

## Session 如何绑定

```
OpenHands:
  create_session → conversation_id → 绑定到 Agent
  每个 conversation 有独立 Agent 实例

MBclaw 当前:
  按 code (设备码) 复用 session
  global-{code} → 单会话模式
  所有通道共享同一 session (如果 code 相同)
```

## 推荐指数

★★☆☆☆ — OpenHands Gateway 是 Web-only，MBclaw 需要多渠道
