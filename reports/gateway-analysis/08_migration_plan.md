# 任务八：Gateway 迁移计划

> Gateway 已有良好基础，重点是统一三条路径 + 补 Session/Auth/RateLimit。

---

## Phase 1 — 统一 StandardMessage 协议（0.5 天）

### 目标
消除 agent.py + wechat.py 两处 StandardMessage 重复定义

### 新增
```
gateway/protocol.py              ← StandardMessage + GatewayAgentReply
```

### 修改
```
agent.py StandardMessage         → 删除，import from gateway.protocol
gateway/adapters/wechat.py       → import from gateway.protocol
gateway/normalize.py             → import from gateway.protocol
gateway/router.py                → import from gateway.protocol
gateway/dispatcher.py            → import from gateway.protocol
```

### Phase 1 完成标准
- 全项目仅一处 StandardMessage 定义
- 所有模块引用 gateway.protocol

---

## Phase 2 — 统一 Runtime 入口（1 天）

### 目标
三条路径 → 一条：Gateway → Runtime

### 新增
```
gateway/session_resolver.py      ← SessionResolver
```

### 修改
```
gateway/router.py MessageRouter:
  删除 MotherAgent.send() 绑定
  改为: send_to_runtime(msg) → Runtime.enqueue(msg)
  Runtime 通过 gateway/protocol GatewayAgentReply 回复

gateway_agent.py:
  handle_gateway_agent() 删除
  WeChat → 走统一 Gateway → Runtime 通道

agent.py MotherAgent:
  删除 (MotherRuntime 替代)
```

### 修改 main.py
```
WeChat 注册:
  旧: set_on_message(handle_gateway_agent)
  新: set_on_message(lambda msg: gateway.send_to_runtime(msg))

POST /agent/run:
  旧: agent_run(db, session_id, ...)
  新: gateway.send_to_runtime(StandardMessage(...))
```

### Phase 2 完成标准
- 所有消息经过 Gateway → Runtime 唯一通道
- gateway_agent.py 删除
- MotherAgent 删除
- 行为与当前一致

---

## Phase 3 — Session 管理（0.5 天）

### 目标
user_id + channel → 确定性 session_id

### 修改
```
gateway/session_resolver.py:
  resolve(user_id, channel):
    当前: f"global-{user_id}"  (保持兼容)
    远期: f"{channel}:{user_id}"
  resolve_or_create(user_id, channel):
    检查 DB 或 auto-create

gateway/router.py:
  send_to_runtime() 前调 SessionResolver
```

### Phase 3 完成标准
- session_id 由 SessionResolver 统一生成
- 不依赖 hash() (碰撞风险)
- 同一 user+channel 永远映射同一 session

---

## Phase 4 — Auth + Rate Limit（0.5 天）

### 目标
基础认证 + 速率限制

### 新增
```
gateway/auth/gateway_auth.py     ← GatewayAuth
gateway/ratelimit.py             ← GatewayRateLimiter
```

### 修改
```
gateway/ 主流程: 增加 auth + ratelimit 检查点
main.py middleware: 删除 /admin/client/ 简单限流 → 用 GatewayRateLimiter
```

### Phase 4 完成标准
- Gateway 有 authenticate() 调用点 (当前 skip, 预留)
- Per user per channel 速率限制生效
- 超限返回 429 + "请稍后再试"

---

## Phase 5 — 目录整理 + Mobile Channel（1 天）

### 目标
重命名 adapters/ → channels/，新增 MobileAdapter

### 修改
```
gateway/adapters/ → gateway/channels/ (重命名)
gateway/__init__.py → gateway/registry.py (拆出)
gateway/router.py → 删除 (合并到 gateway/__init__.py Gateway.send_to_runtime)
gateway/dispatcher.py → 保持
gateway/normalize.py → 保持
```

### 新增
```
gateway/channels/mobile.py       ← MobileAdapter
  POST /gateway/mobile/message → StandardMessage → Runtime
  Runner 或 App 直接 HTTP 调用
```

### Phase 5 完成标准
- 5 个 Adapter (QQ/WeChat/Feishu/Web/CLI) + 1 个 Mobile
- 目录结构清晰: channels/normalizer/dispatcher/registry/protocol/session_resolver/auth/ratelimit

---

## 工作量汇总

| Phase | 内容 | 天数 | 影响 |
|-------|------|------|------|
| Phase 1 | StandardMessage 统一 | 0.5 天 | 6 文件 import 修改 |
| Phase 2 | 统一 Runtime 入口 | 1 天 | router.py + gateway_agent.py + MotherAgent 删除 |
| Phase 3 | Session 管理 | 0.5 天 | session_resolver.py 新建 |
| Phase 4 | Auth + Rate Limit | 0.5 天 | auth/ + ratelimit.py 新建 |
| Phase 5 | 目录整理 + Mobile | 1 天 | 重命名 + mobile adapter |
| **总计** | | **3.5 天** | |

## 优先级

Gateway 是 **P1 优先级**（与 Scheduler 同级，但应在 Runtime 完成后做）。

原因:
- 当前三条路径不一致 → 行为差异 Bug
- 但改动量小 (3.5 天)，且大部分已有代码可复用
- 必须先有统一 Runtime (Phase 1) 才能统一入口

---

## 单用户 → 多用户扩展路径

```
当前 (Phase 3 后):
  user_id = device_code
  session_id = f"global-{device_code}"

未来 (远期):
  user_id = f"{channel}:{channel_user_id}"  (QQ: qq:123456)
  session_id = f"{channel}:{user_id}"
  user_profiles 表关联 user_id → 偏好/习惯
  GatewayAuth 验证 channel 凭证
  GatewayRateLimiter per user per channel
```

**当前建议**: 保持单用户模式，SessionResolver 只用 `f"global-{code}"`。
不在此阶段设计多用户系统。
