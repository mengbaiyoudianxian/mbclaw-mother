# 任务三：OpenClaw Gateway

> OpenClaw 是一套微信/QQ/飞书 Bot 框架，Gateway 是其核心抽象。

## 为什么 Gateway 独立

```
OpenClaw 设计原则:
  Gateway 是"外部世界的门" — 所有消息进出都经过 Gateway
  Runtime 不关心消息来源 — 只处理 StandardMessage
  Channel 可以随时插拔 — 注册/注销 Adapter 不影响核心逻辑
```

## Channel Adapter 设计

```
OpenClaw Adapter 接口 (推断):
  class ChannelAdapter:
      name: str
      async start()          启动通道 (登录/连接)
      async stop()           停止通道
      async on_message(cb)   注册消息回调
      async send(target, msg) 发送消息

设计模式: Adapter Pattern
  每个 Channel 实现相同接口
  Gateway 只依赖接口, 不依赖具体实现
```

## Message Normalization

```
OpenClaw 标准化流程:
  Raw Input (QQ/WeChat/Feishu) → StandardMessage:
    {
      message_id: str      唯一消息 ID
      channel: str         来源: qq/wechat/feishu
      user_id: str         发送者 ID
      content: str         文本内容
      content_type: str    text/image/voice/file
      timestamp: float     时间戳
      metadata: dict       通道特有元数据
    }
```

## Session Routing

```
OpenClaw Session 策略:
  session_id = f"{channel}:{user_id}"  ← 通道+用户复合键
  同一用户在同一通道 → 同一 Session
  不同通道 → 不同 Session (但可关联到同一 User)

MBclaw 当前:
  sid = abs(hash(f"gateway:{code}")) % 100000
  问题: hash 碰撞 + 无 channel 区分
```

---

## 可迁移到 MBclaw 的设计

| OpenClaw 设计 | MBclaw Gateway | 优先级 |
|--------------|---------------|--------|
| **Channel Adapter 接口** | ✅ 已有 AdapterBase | 一致 |
| **StandardMessage 协议** | 🟡 agent.py 已有，但多处重复定义 | P1 |
| **复合 session_id** | ❌ 用 hash(code) 无 channel | P0 |
| **通道插拔** | ✅ GatewayRegistry | 一致 |
| **消息回调** | ✅ set_on_message() | 一致 |
| **独立 Gateway 层** | 🟡 已独立但三条路径不一致 | P0 |

## 推荐指数

★★★★★ — Gateway 独立 + Channel Adapter 模式 → MBclaw 已有基础，只需统一
