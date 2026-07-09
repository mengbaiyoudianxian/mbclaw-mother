# 任务一：当前 Gateway 状态

## 结论：Gateway 架构已存在且设计合理

`app/gateway/` 目录已有 11 个文件，架构清晰。

---

## 已存在的入口

| 入口 | Adapter | 状态 | 接入方式 |
|------|---------|:---:|------|
| CLI | `CliAdapter` | ✅ 完整 | WebSocket |
| Web | `WebAdapter` | ✅ 完整 | HTTP (FastAPI) |
| QQ | `QQBotAdapter` | ✅ 完整 | WebSocket (官方Bot API v2) |
| WeChat | `WechatAdapter` | ✅ 完整 | 扫码登录 + 长轮询 |
| Feishu | `FeishuAdapter` | 🟡 基础 | HTTP Webhook |
| Mobile | — | ❌ 缺失 | 设备端直接调 API |

---

## 当前消息流程（两条路径）

### 路径 A：Gateway 正式通道（router → dispatcher）

```
External Input (QQ/WeChat/Feishu/Web/CLI)
    │
    ▼
Channel Adapter (start → poll/listen → on_message callback)
    │
    ▼
MessageNormalizer.normalize(channel, raw)  → StandardMessage
    │
    ▼
MessageRouter.send_to_agent(msg)
    │  → MotherAgent.enqueue()
    │  → MotherAgent.process_one()
    │  → MotherAgent.send()  (简单单轮 LLM 调用)
    │
    ▼
ResponseDispatcher.dispatch(msg, reply)
    │  → format_for_channel(channel, text)
    │  → adapter.send(user_id, formatted, meta)
    │
    ▼
User
```

### 路径 B：WeChat 快捷通道（gateway_agent.py — main.py 直接注册）

```
WeChat message → WechatAdapter._on_message callback
    │
    ▼
handle_gateway_agent(msg, code)
    │  → MotherRuntime.run(msg, session_id)
    │  → strip markdown
    │
    ▼
return reply (同步字符串)
```

---

## 问题：两条路径不一致

| | 路径 A (Router) | 路径 B (gateway_agent) |
|:---|:---|:---|
| 使用 Normalizer | ✅ | ❌ (直接传 raw) |
| 使用 Agent 实现 | MotherAgent.send() (简单单轮) | MotherRuntime.run() (完整多轮) |
| Session 管理 | ❌ 无 | ✅ hash(code) → session_id |
| Response 格式化 | ✅ format_for_channel | 🟡 仅 strip markdown |
| Dispatcher 分发 | ✅ adapter.send() | ❌ 直接 return |

---

## 已存在的 Gateway 模块

```
app/gateway/
├── __init__.py          GatewayRegistry (注册中心) + get_registry()
├── normalize.py         MessageNormalizer (5 种 Channel 正常化)
├── router.py            MessageRouter → MotherAgent
├── dispatcher.py        ResponseDispatcher (格式化 + 分发)
└── adapters/
    ├── __init__.py      AdapterBase (抽象接口)
    ├── wechat.py        WechatAdapter (扫码登录 + 长轮询)
    ├── wechat_api.py    WeixinAPI (底层微信 API)
    ├── wechat_auth.py   微信登录凭证管理
    ├── qqbot.py         QQBotAdapter (AppID+Secret → WebSocket)
    ├── feishu.py        FeishuAdapter (HTTP Webhook)
    ├── web.py           WebAdapter (FastAPI HTTP)
    └── cli.py           CliAdapter (WebSocket)
```

---

## 缺失的能力

| 能力 | 说明 | 严重度 |
|------|------|--------|
| **统一消息协议** | StandardMessage 在 agent.py 定义，但 router.py 和 wechat.py 各定义一份 | 🟡 中 |
| **Session 绑定** | gateway_agent.py 用 hash(code) 生成 sid，cli/web 无 session | 🔴 高 |
| **Auth 层** | Gateway 无独立 auth，管理面板有 admin session | 🟡 中 |
| **Rate Limit** | 仅 /admin/client/ 有简单限流 | 🟡 中 |
| **Event 模型** | 无事件抽象 (message_received / reply_ready / error) | 🟢 低 |
| **Gateway ↔ Runtime 协议** | 两条路径用不同的 Agent 实现 | 🔴 高 |
| **MotherAgent.send() 过简** | 单轮 LLM 调用，不走 MotherRuntime 完整流程 | 🔴 高 |
| **Mobile 通道** | 设备端直接调 /agent/run API，不经过 Gateway | 🟡 中 |
