# 任务五：Gateway 最终设计

## 核心定位

```
Gateway:   "连接外部世界"  — 接收 + 验证 + 标准化 + 路由 + 返回
Runtime:   "处理执行"      — Agent Loop + Tool
Context:   "组织上下文"    — Prompt 拼接
Memory:    "保存历史"      — 长期存储
Planner:   "规划任务"      — Task 分解
```

---

## Gateway 职责范围

### ✅ Gateway 负责

| 职责 | 说明 |
|------|------|
| **Channel 管理** | 注册/启动/停止各通道 Adapter |
| **消息接收** | 从各通道接收原始消息 |
| **身份验证** | 验证发送者身份 (user_id / device_code) |
| **消息标准化** | Channel Raw → StandardMessage |
| **Session 解析** | user_id + channel → session_id |
| **消息入队** | 发送到 Runtime (非直接调 LLM) |
| **响应格式化** | Runtime 回复 → 通道格式 |
| **响应分发** | 通过 Channel Adapter 返回用户 |
| **速率限制** | Per channel / per user rate limit |
| **通道状态监控** | Adapter 在线/离线状态 |

### ❌ Gateway 不负责

| 职责 | 归属 | 原因 |
|------|------|------|
| AI 推理 | Runtime | Gateway 只转发 |
| Prompt 构建 | Context Engine | Gateway 不碰 Prompt |
| Memory 查询 | Memory (通过 Context Engine) | Gateway 不存数据 |
| Task Planning | Planner | Gateway 不管执行 |
| Tool 执行 | Capability (Runtime) | Gateway 不执行工具 |
| LLM Key 管理 | TokenPool | Gateway 不知道 Key |

---

## 统一消息协议

```
StandardMessage (唯一定义位置: gateway/protocol.py):
  trace_id: str           UUID 追踪 ID
  channel: str            来源: qq/wechat/feishu/web/cli/mobile
  user_id: str            发送者 ID
  content: str            文本内容
  content_type: str       text/image/voice/file (默认 text)
  timestamp: float        接收时间
  metadata: dict          通道特有数据 (group_id/chat_id/ip)

GatewayAgentReply:
  trace_id: str           对应请求 trace_id
  content: str            回复文本
  channel: str            目标通道
  user_id: str            目标用户
  metadata: dict          通道特有数据
```

## 单用户模式 → 未来扩展

```
当前 (单用户):
  user_id = device_code
  session_id = f"global-{device_code}"
  一个用户一个 session

未来 (多用户):
  user_id = f"{channel}:{channel_user_id}"
  session_id = f"{channel}:{user_id}"
  每个通道+用户组合独立 session

扩展点:
  user_id    → 从 device_code 抽象为通用 user identifier
  session_id → 从 global-{code} 改为 channel-aware
  channel_id → 已有 (channel 字段)
```

---

## 统一的三条路径

```
当前三条路径 → 统一为一条:

External Input (任何通道)
    │
    ▼
Gateway (统一入口)
    │── Channel Adapter 接收
    │── Normalizer → StandardMessage
    │── Auth (可选, 按 channel)
    │── Session Resolve (user_id + channel → session_id)
    │── Enqueue → Runtime
    │
    ▼
Runtime (唯一处理入口)
    │── ContextEngine.build()
    │── Scheduler.dispatch(LLM)
    │── Tool Execution
    │── Reply
    │
    ▼
Gateway (统一出口)
    │── ResponseDispatcher.format_for_channel()
    │── Channel Adapter.send()
    │
    ▼
User
```

## Gateway 不变成 Runtime 的铁律

- Gateway 不 import LLMClient
- Gateway 不 import MemoryRepo
- Gateway 不 import tools.execute()
- Gateway 不 import ContextEngine
- Gateway 只 import: StandardMessage + GatewayAgentReply + ChannelAdapter
- Gateway 与 Runtime 的接口: enqueue(message) → await reply()
