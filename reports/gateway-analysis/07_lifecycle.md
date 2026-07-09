# 任务七：Gateway 完整生命周期

## 消息接收 → 回复完整链路

```
[1] External Input
    用户通过某渠道发送消息:
    ├── QQ: 群聊/私聊 文本
    ├── WeChat: 好友/群聊 文本
    ├── Feishu: 群聊 文本
    ├── Web: HTTP POST /gateway/web/message
    ├── CLI: WebSocket 文本
    └── Mobile: HTTP POST /gateway/mobile/message (远期)
    │
    ▼
[2] Channel Adapter 接收
    Adapter 持续监听 (长轮询/WebSocket/HTTP):
    ├── WeChat: 长轮询 syncCheck → 收到 MsgId → 下载消息
    ├── QQ: WebSocket → C2C_MESSAGE_CREATE / GROUP_AT_MESSAGE_CREATE
    ├── Feishu: HTTP Webhook → im.message.receive_v1
    ├── Web: HTTP POST → receive()
    └── CLI: WebSocket → handle_ws()
    状态: receiving
    │
    ▼
[3] Message Normalize
    MessageNormalizer.normalize(channel, raw) → StandardMessage:
    ├── QQ: raw.sender.user_id → user_id, raw.raw_message → content
    ├── WeChat: raw.FromUserName → user_id, raw.Content → content
    ├── Feishu: raw.event.sender.sender_id → user_id, raw.event.message.content.text → content
    ├── Web: raw.code → user_id, raw.message → content
    └── CLI: raw.code → user_id, raw.message → content
    输出: StandardMessage {trace_id, channel, user_id, content, metadata}
    状态: normalizing
    │
    ▼
[4] Authentication (可选)
    GatewayAuth.authenticate(channel, credentials):
    ├── 白名单 channel (web/cli) → 跳过
    ├── QQ: verify AppID+Secret → 自动通过
    ├── WeChat: 已登录 → 自动通过
    └── Feishu: verify AppID+Secret → 通过
    状态: authenticating
    │
    ▼
[5] Rate Limit Check
    GatewayRateLimiter.check(channel, user_id):
    ├── 每用户每分钟最多 10 条 (可配置)
    ├── 超出 → 429 "请稍后再试"
    └── 通过 → 继续
    状态: rate_limiting
    │
    ▼
[6] Session Resolve
    SessionResolver.resolve(user_id, channel) → session_id:
    当前 (单用户): f"global-{device_code}"
    未来: f"{channel}:{user_id}"
    ├── Session 存在 + active → 复用
    ├── Session 不存在 → 创建新 Session (create_session)
    └── Session 已关闭 → 创建新 Session
    状态: resolving
    │
    ▼
[7] Enqueue to Runtime
    Gateway.send_to_runtime(msg, session_id):
    ├── 构造 RuntimeMessage
    ├── 入队 (asyncio.Queue / 内存队列)
    └── 非阻塞: 异步等待回复
    状态: enqueuing
    │
    ▼
[8] Runtime 处理
    Runtime (MotherRuntime / agent_run):
    ├── ContextEngine.build() → Prompt
    ├── Scheduler.dispatch(LLM) → 调用 LLM
    ├── Tool Execution (如有)
    ├── 循环 (max_turns=5)
    └── Reply: text
    状态: processing
    │
    ▼
[9] Reply Received
    Runtime 返回 reply:
    ├── text → GatewayAgentReply {trace_id, content, channel, user_id}
    └── error → GatewayAgentReply {trace_id, content="错误: ...", channel, user_id}
    状态: replying
    │
    ▼
[10] Response Format
    ResponseDispatcher.format_for_channel(channel, text):
    ├── QQ: text[:2000] (纯文本, 已去 Markdown)
    ├── WeChat: text (保持原样)
    ├── Feishu: JSON {msg_type: text, content: {text: ...}}
    ├── Web: text (保持原样)
    └── CLI: text (保持原样)
    状态: formatting
    │
    ▼
[11] Dispatcher 发送
    ResponseDispatcher.dispatch(reply):
    ├── adapter = registry.get(channel)
    ├── adapter.send(user_id, formatted_text, metadata)
    │   ├── QQ: POST /v2/users/{openid}/messages
    │   ├── WeChat: POST /webwxsendmsg
    │   ├── Feishu: POST /open-apis/im/v1/messages
    │   ├── Web: reply 存入 _replies dict → poll
    │   └── CLI: ws.send_text(reply)
    └── return success/failure
    状态: dispatching
    │
    ▼
[12] User
    用户收到回复:
    ├── QQ: 群聊/私聊 消息
    ├── WeChat: 好友/群聊 消息
    ├── Feishu: 群聊 消息
    ├── Web: HTTP Response
    └── CLI: WebSocket 文本
    状态: delivered
```

## 状态机

```
external_input → receiving → normalizing
                                │
                         ┌──────┴──────┐
                         ▼             ▼
                    authenticating  (skip auth)
                         │             │
                         └──────┬──────┘
                                ▼
                          rate_limiting
                         ┌──────┴──────┐
                         ▼             ▼
                      allowed       rejected (429)
                         │
                         ▼
                      resolving
                         │
                         ▼
                      enqueuing
                         │
                         ▼
                      processing (Runtime)
                         │
                    ┌────┴────┐
                    ▼         ▼
                 replying   error
                    │         │
                    └────┬────┘
                         ▼
                     formatting
                         │
                         ▼
                     dispatching
                         │
                         ▼
                      delivered
```

## Gateway ↔ Runtime 协议（唯一接口）

```
Gateway → Runtime:
  {
    trace_id: str,
    channel: str,
    user_id: str,
    session_id: str,     ← Gateway 已解析
    content: str,
    timestamp: float
  }

Runtime → Gateway:
  {
    trace_id: str,       ← 对应请求
    content: str,
    channel: str,
    user_id: str
  }
```
