# 任务四：Worker 调度与 Runtime 分工

## Scheduler 定位

```
                    Scheduler
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
    Provider选择    Worker选择    Capability选择
    (哪个LLM)      (哪个Worker)   (哪个工具)
```

---

## Worker 调度设计

### Worker 类型

| Worker | 用途 | 执行方式 |
|--------|------|---------|
| LLM Worker | 调用 LLM API | HTTP POST → 解析响应 |
| Tool Worker | 执行工具 | 本地 Python / subprocess / HTTP |
| Device Worker | 设备操作 | ADB / HTTP 到设备端 |
| Gateway Worker | 消息收发 | Gateway Adapter |

### Worker 选择策略

```
Scheduler.dispatch(step):
  1. 判断 Step 类型:
     ├── LLM_CALL → LLMWorker
     ├── TOOL_CALL → ToolWorker
     │   ├── 本地工具 → 直接执行
     │   ├── 设备工具 → DeviceWorker (需要设备在线)
     │   └── 外部 API → 通过 CapabilityRegistry
     └── REPLY → GatewayWorker

  2. Worker 执行
  3. 收集 Observation
  4. 返回给 Planner/Runtime
```

---

## Scheduler vs Runtime 边界

| 职责 | Scheduler | Runtime | 理由 |
|------|:---:|:---:|------|
| Provider 选择 | ✅ | | Scheduler 选 LLM |
| Key 路由 | ✅ | | Scheduler 选 Key |
| 重试/退避 | ✅ | | Scheduler 控制 |
| Cooldown | ✅ | | Scheduler 管理 |
| HTTP 调用 | ✅ | | Scheduler 执行 |
| 响应解析 | ✅ | | Scheduler 解析 |
| Agent Loop | | ✅ | Runtime 控制流程 |
| 上下文构建 | | ✅ | Runtime 管理 |
| 工具分发 | ✅ | | Scheduler 路由 |
| 工具执行 | | ✅ | Runtime/Capability 执行 |
| Session 管理 | | ✅ | Runtime 管理 |
| Prompt 构建 | | ✅ | Runtime/Context 管理 |

## Scheduler vs TokenPool 边界

| 职责 | Scheduler | TokenPool | 理由 |
|------|:---:|:---:|------|
| Key 存储 | | ✅ | 数据层 |
| Key 状态 (working/failed) | | ✅ | 数据层 |
| Key 选择 (路由) | ✅ | | 逻辑层 |
| Cooldown 状态 | ✅ | | 逻辑层 |
| Rate limit 判断 | ✅ | | 逻辑层 |
| Usage 写入 | | ✅ | 数据层 |
| Health check | ✅ | | 主动探测 |

## Scheduler vs Governor 边界

| 职责 | Scheduler | Governor | 理由 |
|------|:---:|:---:|------|
| 操作权限 | | ✅ | Governor 决策 |
| Provider 许可 | | ✅ | Governor 控制哪些 Provider 可用 |
| 工具许可 | | ✅ | Governor 控制哪些 Tool 可用 |
| 执行调度 | ✅ | | Scheduler 执行 |
| 故障恢复策略 | | ✅ | Governor 制定策略 |
| 故障恢复执行 | ✅ | | Scheduler 执行策略 |

## Scheduler vs Planner 边界

| 职责 | Scheduler | Planner | 理由 |
|------|:---:|:---:|------|
| Goal 分析 | | ✅ | Planner 分析 |
| Task 分解 | | ✅ | Planner 分解 |
| Step 执行 | ✅ | | Scheduler 逐个执行 |
| Replan 触发 | | ✅ | Planner 决定 |
| Replan 后的新 Step | ✅ | | Scheduler 接收新队列 |
