# MBclaw Mother Runtime Specification v1

> **状态**: Phase 0 — Architecture Freeze（设计基线）
> **作者**: MBclaw 架构组
> **日期**: 2026-07-09
> **版本**: v1.0
> **性质**: 设计文档，非实现代码。本阶段禁止编码。

---

## 目录

1. [概述](#1-概述)
2. [Runtime 生命周期](#2-runtime-生命周期)
3. [模块架构](#3-模块架构)
4. [模块详述](#4-模块详述)
5. [调用关系图](#5-调用关系图)
6. [状态流转图](#6-状态流转图)
7. [事件流转图](#7-事件流转图)
8. [代码复用映射](#8-代码复用映射)
9. [目录结构](#9-目录结构)
10. [ADR 索引](#10-adr-索引)

---

## 1. 概述

### 1.1 什么是 Mother Runtime

Mother Runtime 是 MBclaw 的**核心执行引擎**，负责从消息进入（Gateway）到回复完成（Response）的完整生命周期管理。

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| **模块独立** | 每个模块有明确定义的接口，可独立替换 |
| **事件驱动** | 模块间通过事件通信，不直接调用 |
| **Pipeline 模式** | 消息处理是一个有序的 Pipeline，每阶段有明确的输入/输出 |
| **能力注册** | 工具和技能统一注册，运行时动态发现 |
| **无状态计算** | Compute 层无状态，可水平扩展 |
| **有状态上下文** | Context Engine 管理会话状态，支持序列化 |

### 1.3 与现有代码的关系

本规范基于对当前 MBclaw 工程的完整分析（参见 `reports/01-05`）。它**不是重写**，而是**重新组织**现有功能：

- 保留：MotherRuntime、MemoryRepo、Gateway、Tool 执行引擎
- 拆分：将 MotherRuntime 的大单体拆为 Governor + Planner + Context Engine
- 新增：Planner（策略层）、Governor（编排层）
- 删除：agent.py、llm_router.py、tool_runtime.py、mbos_core.py、内置 token_pool.py

---

## 2. Runtime 生命周期

### 2.1 完整生命周期（消息进入 → 回复完成）

```
                          ┌─────────────────────┐
                          │    Gateway 接收消息   │
                          │  (QQ/微信/Web/CLI)   │
                          └──────────┬──────────┘
                                     │ StandardMessage
                                     ▼
┌────────────────────────────────────────────────────────────────────┐
│                        Governor (编排层)                            │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                     Phase 1: Ingress                          │  │
│  │                                                               │  │
│  │  1. Gateway → StandardMessage (归一化)                        │  │
│  │  2. Governor 获取/创建 Session                                │  │
│  │  3. Governor 加载 Context (WorkingMemory)                     │  │
│  │  4. Governor 触发 Memory 检索 (并行)                          │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │                                      │
│  ┌──────────────────────────▼───────────────────────────────────┐  │
│  │                     Phase 2: Planning                         │  │
│  │                                                               │  │
│  │  5. Planner 分析用户意图                                      │  │
│  │  6. Planner 决定是否需要工具                                  │  │
│  │  7. 如需要 → Planner 选择 Capability                         │  │
│  │  8. 如不需要 → 直接生成回复 (跳过 Phase 3)                    │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │                                      │
│  ┌──────────────────────────▼───────────────────────────────────┐  │
│  │                     Phase 3: Execution                        │  │
│  │                                                               │  │
│  │  9. Scheduler 选择 LLM Provider (通过 TokenPool)              │  │
│  │  10. Scheduler 获取 Key + 模型                                │  │
│  │  11. Context Engine 组装 Prompt (System + Memory + History)   │  │
│  │  12. Compute 执行 LLM 调用                                    │  │
│  │  13. 解析输出 → 有 Tool Call? → Capability.execute()         │  │
│  │       └── 循环至 12 (最多 5 轮)                               │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │                                      │
│  ┌──────────────────────────▼───────────────────────────────────┐  │
│  │                     Phase 4: Egress                           │  │
│  │                                                               │  │
│  │  14. Context Engine 更新 WorkingMemory                        │  │
│  │  15. Memory 异步写入 (摘要 + 关键词 + 经验)                   │  │
│  │  16. Governor 返回 reply → Gateway                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │  Gateway 发送回复    │
                          │  (格式化 + 渠道适配) │
                          └─────────────────────┘
```

### 2.2 Session 生命周期

```
                    create_session()
                         │
                         ▼
                   ┌──────────┐
                   │  ACTIVE  │◄──── add_message()
                   └────┬─────┘
                        │
                   close_session()
                        │
                        ▼
                   ┌──────────┐
                   │  CLOSED  │  (不可逆)
                   └──────────┘
```

### 2.3 LLM 调用生命周期（Scheduler 视角）

```
request_llm(messages)
    │
    ▼
Scheduler.select_provider(task, messages)
    │
    ├── 1. 调用 TokenPool API: POST /v1/chat/completions
    │       ├── TokenPool GuardRail (Quota → RateLimit → Circuit)
    │       ├── TokenPool 故障转移 (最多 3 个候选)
    │       └── TokenPool 返回 (response, alias_used)
    │
    ├── 2. TokenPool 不可用 → fallback
    │       └── 使用本地环境变量 MBCLAW_LLM_*
    │
    └── 3. 返回 (response_dict, provider_info)
```

---

## 3. 模块架构

### 3.1 模块总览

```
┌──────────────────────────────────────────────────────────────────┐
│                        Mother Runtime                             │
│                                                                   │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐  │
│  │ Governor │   │ Planner  │   │Scheduler │   │Context Engine│  │
│  │ (编排层) │◄──│(决策层)  │   │(调度层)  │   │(上下文管理)  │  │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └──────┬───────┘  │
│       │              │              │                 │           │
│  ┌────┴─────┐   ┌────┴─────┐   ┌────┴─────┐   ┌──────┴───────┐  │
│  │ Gateway  │   │ Memory   │   │Capability│   │   Compute    │  │
│  │(消息入口)│   │(长期记忆)│   │(能力注册)│   │  (执行层)    │  │
│  └──────────┘   └──────────┘   └──────────┘   └──────────────┘  │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 模块职责矩阵

| 模块 | 一句话职责 | 输入 | 输出 |
|------|-----------|------|------|
| **Gateway** | 多渠道消息归一化 | 原始消息 (QQ/微信/Web) | StandardMessage |
| **Governor** | 会话生命周期编排 | StandardMessage | reply + session_state |
| **Planner** | 意图分析 + 工具选择 | context + intent | Plan (是否需要工具/哪个工具) |
| **Scheduler** | LLM Provider 调度 | messages + task_type | (response, provider_info) |
| **Context Engine** | 会话上下文管理 | messages + memory_hits | assembled_prompt |
| **Memory** | 长期记忆读写 | query_text | MemoryHit[] |
| **Capability** | 工具注册与执行 | tool_name + args | execution_result |
| **Compute** | 底层执行 (shell/http) | command/request | raw_result |

---

## 4. 模块详述

### 4.1 Governor（编排层）

**定位**: Runtime 的最高指挥官，管理会话生命周期，协调所有模块。

**职责**:
- 会话创建/获取/关闭
- 编排 Pipeline 四阶段（Ingress → Planning → Execution → Egress）
- 模块间事件路由
- 错误处理和降级策略

**接口**:
```
Governor
├── create_session(user_id, channel) → session_id
├── get_session(session_id) → Session
├── close_session(session_id) → CloseResult
├── process_message(msg: StandardMessage) → Reply
└── reset_session(session_id)
```

**生命周期**: 进程级单例。Session 状态存储在 Context Engine 中。

**依赖**:
- Gateway → 接收 StandardMessage
- Context Engine → 获取/更新会话上下文
- Planner → 决策下一步行动
- Memory → 检索相关记忆（异步）

**代码复用**: 从 `api.py` 的会话 CRUD + `mother_runtime.py` 的 `_get_session()` 提取。

---

### 4.2 Planner（决策层）

**定位**: 分析用户意图，决定是否需要工具、选哪个工具。

**职责**:
- 分析用户消息意图（chat / command / tool_request）
- 决定是否需要调用 Capability
- 如果不需要工具：直接交给 Scheduler 生成回复
- 如果需要工具：选择最合适的 Capability

**接口**:
```
Planner
├── analyze_intent(message, context) → Intent
└── select_capability(intent, capabilities) → Capability | None
```

**决策树**:
```
用户消息
    │
    ├── 明确技能请求 (如 "帮我审查这段代码")
    │   └── Intent: tool_request → 选择 code-review 技能
    │
    ├── 明确操作请求 (如 "打开微信")
    │   └── Intent: tool_request → 选择 open_app 工具
    │
    ├── 问题 (如 "Python 3.13 有什么新特性")
    │   └── Intent: chat → 不需要工具
    │
    └── 模糊请求 (如 "帮我看看")
        └── Intent: ambiguous → Scheduler 让 LLM 自己决定
```

**依赖**:
- Context Engine → 获取上下文判断意图
- Capability → 获取可用能力列表

**代码复用**: 当前 MotherRuntime 中隐式在 system prompt 和工具解析中实现。需提取为独立模块。

---

### 4.3 Scheduler（调度层）

**定位**: LLM Provider 调度的唯一入口，封装 TokenPool 交互。

**职责**:
- 调用 TokenPool HTTP API 获取 LLM 响应
- 管理 Provider fallback 策略
- 记录调用 metrics
- TokenPool 不可用时的本地降级

**接口**:
```
Scheduler
├── request_llm(messages, task_type, strategy) → LLMResponse
├── get_available_providers() → ProviderInfo[]
└── health_check() → ProviderHealth[]
```

**调用 TokenPool 的方式**:
```
POST http://${TOKENPOOL_HOST}:8100/v1/chat/completions
{
  "model": "...",        // 可选，不指定则由 TokenPool 自动选择
  "messages": [...],
  "max_tokens": 2048,
  "temperature": 0.3
}
```

**依赖**:
- TokenPool 服务（外部 HTTP）
- 本地环境变量（fallback）

**代码复用**: 从 `mother_runtime.py` 的 `_build_candidates()` 提取，改为 HTTP 调用。

---

### 4.4 Context Engine（上下文管理）

**定位**: 管理会话的短期上下文（WorkingMemory）。

**职责**:
- 存储/检索会话消息历史
- Token 预算管理
- 自动压缩（达到 80% 阈值时）
- 组装最终 Prompt（System + Memory + History + User）
- 支持序列化/反序列化

**接口**:
```
ContextEngine
├── get_context(session_id) → WorkingMemory
├── add_message(session_id, role, content)
├── assemble_prompt(session_id, system_prompt, memory_hits) → messages[]
├── estimate_tokens() → int
├── compress(session_id) → None
├── serialize(session_id) → dict
└── deserialize(session_id, data) → WorkingMemory
```

**Prompt 组装顺序**:
```
assemble_prompt(session_id):
    messages = []
    messages.append({role: "system", content: SYSTEM_PROMPT})
    messages.append({role: "system", content: memory_recall})
    messages.extend(recent_history[-20:])
    messages.append({role: "user", content: current_message})
    return messages
```

**依赖**: Memory（获取 memory_recall）

**代码复用**: 从 `mother_runtime.py` 的 `WorkingMemory` 类直接迁移。

---

### 4.5 Memory（长期记忆）

**定位**: 双路召回长期记忆系统。

**职责**:
- 写入：摘要 + 关键词 + 经验
- 检索：FTS5 全文 + jieba 关键词 双路召回
- 经验检索：FTS5 + kind-priority + recency
- 新会话注入：上次关键事实 + 教训
- 归档：超量经验自动归档

**接口**:
```
Memory
├── write(session_id, summary, keywords, experiences) → None
├── query(text, top_n) → MemoryHit[]
├── query_experiences(text, top_n) → ExperienceHit[]
├── render_injection(exclude_session_id) → str | None
└── evict() → int
```

**数据库模型**（保持不变）:
```
sessions, messages, summaries, keywords, experiences
+ FTS5: messages_fts, experiences_fts
```

**依赖**: Database (SQLite)

**代码复用**: 几乎完整复用 `memory.py` + `models.py` + `schema/fts.sql`。

---

### 4.6 Capability（能力注册）

**定位**: 统一的工具和技能注册中心。

**职责**:
- 注册工具（file/shell/device/web/memory）
- 注册技能（GitHub/SSH/code-review/PRD 等 prompt-based）
- 能力发现（按 category/tag 查询）
- 能力执行（dispatch 到对应 handler）
- 使用统计

**接口**:
```
Capability
├── register(name, handler, category, tags, description) → None
├── unregister(name) → None
├── list(category, tag) → CapabilityDef[]
├── search(query) → CapabilityDef[]
├── execute(name, args) → ExecutionResult
├── get_usage(name) → UsageStats
└── bump_usage(name) → None
```

**能力分类**:
```
能力类型:
  ├── tool (有实际代码执行):
  │   ├── file: read_file, write_file, edit_file, list_directory
  │   ├── shell: run_command
  │   ├── device: device_status, open_app, toggle_wifi, ...
  │   ├── web: web_search, open_url
  │   └── memory: search_memory, list_sessions
  │
  ├── skill (有实际代码执行):
  │   ├── github: search_code, create_pr, pr_review, ...
  │   └── ssh: ssh_exec
  │
  └── prompt_skill (纯 LLM prompt 指令):
      ├── code-review, code-simplifier, security
      ├── prd, release-notes, research-brief
      └── frontend-design, ui-ux-pro-max, ...
```

**依赖**: Compute（底层执行）

**代码复用**: 合并 `tools.py` + `skills.py` + `tool_runtime.py`。

---

### 4.7 Gateway（消息入口）

**定位**: 多渠道消息的归一化和适配。

**职责**:
- 接收各渠道消息
- 归一化为 StandardMessage
- 回复格式化（渠道适配）
- 渠道生命周期管理

**接口**:
```
Gateway
├── register_adapter(name, adapter) → None
├── receive(channel, raw_message) → StandardMessage
├── send(channel, reply, original_message) → None
└── list_adapters() → AdapterInfo[]
```

**支持的渠道**:
```
adapters/
├── wechat.py     (微信 Bot)
├── wechat_api.py (微信 API)
├── qqbot.py      (QQ Bot)
├── web.py        (Web Chat)
├── cli.py        (CLI)
└── feishu.py     (飞书)
```

**依赖**: 无（独立模块）

**代码复用**: 从 `gateway/` + `gateway_agent.py` 完整迁移。

---

### 4.8 Compute（执行层）

**定位**: 底层执行引擎，处理实际的系统调用、HTTP 请求、设备命令。

**职责**:
- Shell 命令执行（带安全过滤）
- HTTP 请求代理
- 设备命令下发
- 执行结果标准化

**接口**:
```
Compute
├── run_command(cmd, timeout, cwd) → CommandResult
├── http_request(method, url, headers, body) → HTTPResult
├── send_device_command(device_code, command) → DeviceResult
└── read_file(path) → FileContent
```

**安全策略**:
```
blocked_commands = [
    "rm -rf /", "shutdown", "reboot", "mkfs", "dd if=",
    ":(){ :|:& };:",  // fork bomb
]
```

**依赖**: 操作系统

**代码复用**: 从 `tools.py` 的 `run_command`、`device_tool_execute` 等提取。

---

## 5. 调用关系图

### 5.1 主流程调用链

```
Gateway.receive()
    │
    │ StandardMessage
    ▼
Governor.process_message(msg)
    │
    ├──(1)──► ContextEngine.get_context(session_id)
    │
    ├──(2)──► Memory.query(msg.content)  ← 并行
    │           └── context_hits
    │
    ├──(3)──► Planner.analyze_intent(msg, context)
    │           └── Intent {type, confidence, suggested_tools}
    │
    ├──(4)──► [if Intent.type == "tool_request"]
    │           ├── Planner.select_capability(intent, capabilities)
    │           ├── ContextEngine.assemble_prompt(session_id, system, memory)
    │           │   └── messages[]
    │           ├── Scheduler.request_llm(messages, task_type)
    │           │   └── LLMResponse {content, tool_calls}
    │           ├── [if tool_calls]
    │           │   └── Capability.execute(tool_name, args)
    │           │       └── Compute.run_command() / Compute.http_request()
    │           │           └── result → 反馈给 ContextEngine → 循环
    │           └── final_reply
    │
    ├──(5)──► [if Intent.type == "chat"]
    │           ├── ContextEngine.assemble_prompt(...)
    │           └── Scheduler.request_llm(messages, "chat")
    │               └── final_reply
    │
    ├──(6)──► ContextEngine.add_message(session_id, "assistant", reply)
    │
    ├──(7)──► Memory.write(...)  ← 异步 (不阻塞回复)
    │
    └──(8)──► Gateway.send(channel, reply)
```

### 5.2 模块依赖图

```
                    ┌──────────┐
                    │ Gateway  │ (独立)
                    └────┬─────┘
                         │
                         ▼
                    ┌──────────┐
                    │ Governor │ (编排，依赖所有)
                    └────┬─────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │ Planner  │   │Context   │   │ Memory   │
   │          │   │Engine    │   │          │
   └────┬─────┘   └────┬─────┘   └──────────┘
        │              │
        ▼              ▼
   ┌──────────┐   ┌──────────┐
   │Capability│   │Scheduler │
   └────┬─────┘   └────┬─────┘
        │              │
        ▼              │ HTTP
   ┌──────────┐        ▼
   │ Compute  │  ┌──────────┐
   └──────────┘  │TokenPool │ (外部服务)
                 └──────────┘
```

---

## 6. 状态流转图

### 6.1 Session 状态机

```
                create_session()
                     │
                     ▼
               ┌──────────┐
               │  ACTIVE  │
               └────┬─────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
   add_message  process_msg  (idle)
        │           │           │
        └───────────┼───────────┘
                    │
              close_session()
                    │
                    ▼
               ┌──────────┐
               │  CLOSED  │ (终态)
               └──────────┘
```

### 6.2 Agent Loop 状态机

```
                    ┌──────────┐
                    │   IDLE   │
                    └────┬─────┘
                         │ receive message
                         ▼
                    ┌──────────┐
                    │ PLANNING │
                    └────┬─────┘
                         │
              ┌──────────┴──────────┐
              │                     │
       intent=chat            intent=tool
              │                     │
              ▼                     ▼
        ┌──────────┐          ┌──────────┐
        │GENERATING│          │SCHEDULING│
        └────┬─────┘          └────┬─────┘
             │                     │
             │                     ▼
             │               ┌──────────┐
             │               │EXECUTING │
             │               └────┬─────┘
             │                    │
             │           ┌────────┴────────┐
             │           │                 │
             │     has_tool_calls     no_tool_calls
             │           │                 │
             │     ┌─────┘                 │
             │     ▼                       │
             │  ┌──────────┐              │
             │  │ TOOL_RUN │────┐         │
             │  └──────────┘    │         │
             │     │            │         │
             │     │ turns < 5  │ turns>=5│
             │     │            │         │
             │     └────────────┘         │
             │           │                │
             └───────────┴────────────────┘
                         │
                         ▼
                    ┌──────────┐
                    │COMPLETING│
                    └────┬─────┘
                         │
                         ▼
                    ┌──────────┐
                    │   IDLE   │
                    └──────────┘
```

---

## 7. 事件流转图

### 7.1 事件类型

```
事件总线 (EventBus)

事件类型:
  ├── session.created     (session_id, user_id, channel)
  ├── session.message     (session_id, message)
  ├── session.closed      (session_id, summary)
  ├── memory.written      (session_id, memory_id)
  ├── memory.hit          (session_id, hits[])
  ├── tool.called         (session_id, tool_name, args)
  ├── tool.completed      (session_id, tool_name, result)
  ├── llm.requested       (session_id, provider, model)
  ├── llm.completed       (session_id, provider, model, tokens, latency)
  ├── llm.failed          (session_id, provider, error)
  ├── scheduler.fallback  (reason)
  └── runtime.error       (session_id, error)
```

### 7.2 一次完整对话的事件序列

```
session.created
    │
session.message       ← 用户消息
    │
memory.hit            ← 检索到相关记忆
    │
llm.requested         ← 调用 LLM
    │
llm.completed         ← LLM 响应
    │
(条件) tool.called    ← 如果有工具调用
    │
tool.completed        ← 工具执行结果
    │
llm.requested         ← 再次调用 LLM (带工具结果)
    │
llm.completed         ← 最终回复
    │
session.message       ← 回复写入
    │
(异步) memory.written ← 记忆持久化
```

### 7.3 事件消费者

```
EventBus
    │
    ├── Memory.writer      ← 订阅 session.closed → 异步写记忆
    ├── MetricsCollector   ← 订阅 llm.*, tool.* → 收集指标
    ├── AdminNotifier      ← 订阅 runtime.error → 告警通知
    └── AuditLogger        ← 订阅全部事件 → 审计日志
```

---

## 8. 代码复用映射

### 8.1 当前代码 → 目标模块

| 当前文件 | 目标模块 | 复用度 | 处理方式 |
|---------|---------|--------|---------|
| `mother_runtime.py` | Governor + Context Engine | 70% | 拆分为两个模块 |
| `memory.py` | Memory | 95% | 直接复用 |
| `models.py` | Memory (DB 层) | 100% | 直接复用 |
| `db.py` | Memory (DB 层) | 100% | 直接复用 |
| `schema/fts.sql` | Memory (DB 层) | 100% | 直接复用 |
| `llm.py` | Scheduler (部分) | 30% | 保留 chat()，删除 fallback |
| `tools.py` | Capability + Compute | 60% | 合并到 Capability Registry |
| `skills.py` | Capability | 80% | 注册到 Capability Registry |
| `pipeline.py` | Governor (close_session) | 80% | 迁移到 Governor |
| `gateway_agent.py` | Gateway | 90% | 直接复用 |
| `gateway/` | Gateway (adapters) | 100% | 直接复用 |
| `api.py` | API 层 | 70% | 保留会话 API，删除内置端点 |

### 8.2 需要新增的代码

| 模块 | 新增内容 | 预估行数 |
|------|---------|---------|
| Governor | 编排器 + Session 管理 | ~200 |
| Planner | 意图分析 + 工具选择 | ~150 |
| Scheduler | TokenPool HTTP 客户端 | ~100 |
| Context Engine | WorkingMemory (从 mother_runtime 拆出) | ~150 |
| Capability | 统一注册表 | ~200 |
| EventBus | 进程内事件总线 | ~100 |

### 8.3 可以淘汰的代码（仅标记）

| 文件 | 淘汰时间 | 理由 |
|------|---------|------|
| `agent.py` | Phase 1 | 功能被 Governor + Planner 覆盖 |
| `agent.py.phase2.bak` | Phase 1 | 备份 |
| `agent.py.phaseb.bak` | Phase 1 | 备份 |
| `llm_router.py` | Phase 1 | 功能被 Scheduler 覆盖 |
| `tool_runtime.py` | Phase 2 | 合并入 Capability + Compute |
| `mbos_core.py` | Phase 1 | 早期原型 |
| `output_sanitizer.py` | Phase 1 | 仅 MBOSCore 使用 |
| `providers.py` | Phase 1 | TokenPool 替代 |
| `token_pool.py` (Mother内置) | Phase 1 | Scheduler 通过 HTTP 调 TokenPool |
| `capabilities/` | Phase 1 | 仅数据模型，无消费者 |
| `admin/` 中 ~25 个废弃/重复文件 | Phase 3 | 见 03_ControlPanel_Review.md |

---

## 9. 目录结构

### 9.1 目标目录树

```
mother/
├── main.py                     # FastAPI 入口
│
├── core/                       # 核心引擎
│   ├── __init__.py
│   ├── governor.py             # Governor — 编排层
│   ├── planner.py              # Planner — 决策层
│   ├── scheduler.py            # Scheduler — LLM 调度层
│   ├── context_engine.py       # Context Engine — 上下文管理
│   └── pipeline.py             # close_session (从 app/pipeline.py 迁移)
│
├── memory/                     # 长期记忆 (完整保留)
│   ├── __init__.py
│   ├── repo.py                 # MemoryRepo (从 app/memory.py 迁移)
│   ├── models.py               # ORM 模型 (从 app/models.py 迁移)
│   └── schema/
│       └── fts.sql             # FTS5 索引
│
├── capability/                 # 能力注册
│   ├── __init__.py
│   ├── registry.py             # ToolRegistry
│   ├── tools/                  # 内置工具
│   │   ├── file.py
│   │   ├── shell.py
│   │   ├── device.py
│   │   └── web.py
│   ├── skills/                 # 高级技能
│   │   ├── github.py
│   │   ├── ssh.py
│   │   └── prompt_skills.py    # LLM prompt-based 技能
│   └── providers/              # API Provider (TokenPool + 本地)
│       ├── tokenpool.py        # TokenPool HTTP 客户端
│       └── local.py            # 本地环境变量 fallback
│
├── gateway/                    # 消息网关
│   ├── __init__.py
│   ├── agent.py                # gateway_agent (从 app/gateway_agent.py 迁移)
│   ├── router.py
│   ├── normalize.py
│   └── adapters/
│       ├── wechat.py
│       ├── qqbot.py
│       ├── web.py
│       ├── cli.py
│       └── feishu.py
│
├── compute/                    # 执行层
│   ├── __init__.py
│   ├── executor.py             # 统一执行入口
│   ├── shell.py                # shell 命令执行
│   ├── http_client.py          # HTTP 请求
│   └── device.py               # 设备命令
│
├── api/                        # REST API
│   ├── __init__.py
│   ├── sessions.py             # 会话 CRUD
│   ├── agent.py                # Agent 端点
│   ├── admin.py                # 管理面板 API
│   └── dependencies.py         # FastAPI 依赖注入
│
├── db/                         # 数据库
│   ├── __init__.py
│   └── engine.py               # SQLite 引擎 (从 app/db.py 迁移)
│
├── event/                      # 事件系统
│   ├── __init__.py
│   ├── bus.py                  # EventBus
│   └── types.py                # 事件类型定义
│
└── config/                     # 配置
    ├── __init__.py
    └── settings.py             # 统一配置管理
```

### 9.2 模块 README 位置

```
architecture/modules/
├── governor/README.md
├── planner/README.md
├── scheduler/README.md
├── context_engine/README.md
├── memory/README.md
├── capability/README.md
├── gateway/README.md
└── compute/README.md
```

---

## 10. ADR 索引

| ADR | 标题 | 状态 |
|-----|------|------|
| ADR-001 | 选择事件驱动架构 | Accepted |
| ADR-002 | Mother 通过 HTTP 调用 TokenPool | Accepted |
| ADR-003 | 保留 SQLite + FTS5 作为长期记忆存储 | Accepted |
| ADR-004 | 统一工具注册表替代分散定义 | Accepted |
| ADR-005 | Governor 作为单一编排入口 | Accepted |
| ADR-006 | Planner 作为显式决策层（而非隐式在 prompt 中） | Accepted |
| ADR-007 | Context Engine 独立于 Governor | Accepted |
| ADR-008 | Compute 作为无状态执行层 | Accepted |

---

## 附录

### A. 术语表

| 术语 | 定义 |
|------|------|
| **Governor** | 编排层，管理会话生命周期，协调各模块 |
| **Planner** | 决策层，分析意图，选择工具 |
| **Scheduler** | 调度层，LLM Provider 调用的唯一入口 |
| **Context Engine** | 上下文管理，WorkingMemory + Prompt 组装 |
| **Memory** | 长期记忆，双路召回 |
| **Capability** | 能力注册，工具+技能统一管理 |
| **Gateway** | 消息入口，多渠道适配 |
| **Compute** | 执行层，shell/HTTP/device 底层操作 |
| **StandardMessage** | 跨渠道统一消息格式 |
| **WorkingMemory** | 会话短期上下文 |

### B. 相关文档

- `reports/01_Mother_Review.md` — Mother 详细分析
- `reports/02_TokenPool_Review.md` — TokenPool 详细分析
- `reports/04_Architecture_Review.md` — 整体架构评审
- `reports/05_改造建议.md` — 改造路线图
- `adr/ADR-001~008` — 架构决策记录
