# 任务六：Gateway 目录设计

```
gateway/
├── __init__.py              Gateway 模块入口
│   class Gateway:
│       register_adapter(name, adapter)
│       start() → 启动所有 Adapter
│       stop() → 停止所有 Adapter
│       send(reply: GatewayAgentReply) → 分发回复
│       职责: Gateway 总控
│       来源: 替代当前 GatewayRegistry + MessageRouter + ResponseDispatcher
│       当前已有: part
│
├── protocol.py             消息协议 (唯一标准定义)
│   @dataclass
│   class StandardMessage:
│       trace_id, channel, user_id, content, content_type, timestamp, metadata
│   @dataclass
│   class GatewayAgentReply:
│       trace_id, content, channel, user_id, metadata
│       职责: Gateway ↔ Runtime 的唯一协议
│       来源: 替代 agent.py StandardMessage + wechat.py StandardMessage 重复定义
│       当前已有: agent.py StandardMessage (但多处重复)
│
├── registry.py             Adapter 注册中心
│   class AdapterRegistry:
│       register(name, adapter)
│       unregister(name)
│       get(name) → Adapter
│       list_channels() → [name]
│       start_all() / stop_all()
│       职责: 管理所有 Channel Adapter
│       来源: 替代当前 gateway/__init__.py GatewayRegistry
│       当前已有: ✅ 完整
│
├── normalizer.py           消息标准化
│   class MessageNormalizer:
│       normalize(channel, raw) → StandardMessage
│       策略: channel 分发 → _norm_qq / _norm_wechat / _norm_feishu / ...
│       职责: 各通道原始消息 → 统一 StandardMessage
│       来源: 当前 gateway/normalize.py (直接复用)
│       当前已有: ✅ 完整
│
├── session_resolver.py     Session 解析
│   class SessionResolver:
│       resolve(user_id, channel) → session_id
│       resolve_or_create(user_id, channel) → session_id
│       策略: f"{channel}:{user_id}" → 唯一 session
│       职责: user_id + channel → session_id 映射
│       来源: 替代 gateway_agent.py hash("gateway:{code}")
│       当前已有: ❌ 缺失 (当前用 hash)
│
├── dispatcher.py           响应分发
│   class ResponseDispatcher:
│       format_for_channel(channel, text) → formatted_text
│       dispatch(reply: GatewayAgentReply) → bool
│       职责: 格式化回复 → 通过 Adapter 发送
│       来源: 当前 gateway/dispatcher.py (直接复用)
│       当前已有: ✅ 完整
│
├── auth/                   认证层
│   ├── __init__.py
│   └── gateway_auth.py     Gateway 认证
│       class GatewayAuth:
│           authenticate(channel, credentials) → user_id
│           verify(channel, user_id, token) → bool
│           职责: 验证消息发送者身份
│           来源: 替代 admin/router.py _check_session (仅 admin)
│           当前已有: 🟡 仅 admin 有, gateway 无
│
├── ratelimit.py            速率限制
│   class GatewayRateLimiter:
│       check(channel, user_id) → bool  (是否允许)
│       record(channel, user_id)
│       策略: 滑动窗口 per user per channel
│       职责: 防止单用户刷屏
│       来源: 替代 main.py middleware 简单限流
│       当前已有: 🟡 仅 /admin/client/ 有
│
└── channels/               Channel Adapters (重命名自 adapters/)
    ├── __init__.py         ChannelAdapter (抽象接口)
    ├── qqbot.py            QQBotAdapter
    ├── wechat.py           WechatAdapter
    ├── wechat_api.py       WeixinAPI (底层)
    ├── wechat_auth.py      微信登录凭证
    ├── feishu.py           FeishuAdapter
    ├── web.py              WebAdapter
    ├── cli.py              CliAdapter
    └── mobile.py           MobileAdapter (远期)
        职责: 各通道的消息收发
        来源: 当前 gateway/adapters/ (重命名)
        当前已有: ✅ 5 个 Adapter
```

## 与当前 gateway/ 的映射

| 当前 | 新设计 | 状态 |
|------|--------|:---:|
| gateway/__init__.py (GatewayRegistry) | registry.py | 拆出 |
| gateway/normalize.py | normalizer.py | 复用 ✅ |
| gateway/router.py (MessageRouter) | 删除 → Gateway.send() 直接调 Runtime | ❌ |
| gateway/dispatcher.py | dispatcher.py | 复用 ✅ |
| gateway/adapters/ | channels/ | 重命名 |
| agent.py StandardMessage | protocol.py | 统一 |
| gateway_agent.py | 删除 → Gateway.send() 直接调 Runtime | ❌ |
| — | session_resolver.py | 新建 |
| — | auth/ | 新建 |
| — | ratelimit.py | 新建 |
