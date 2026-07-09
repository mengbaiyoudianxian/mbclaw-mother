# Mother Runtime 改造计划

## 目前有什么

| 模块 | 文件 | 状态 |
|------|------|------|
| **Agent Loop** | mother_runtime.py | ✅ 可用，session-aware agent loop |
| **Agent Loop (旧)** | agent.py | ⚠️ 功能重复，基本不用 |
| **WorkingMemory** | mother_runtime.py (内部类) | ✅ 可用，有压缩机制 |
| **MemoryRepo** | memory.py | ✅ 可用，双路召回 |
| **LLMClient** | llm.py | ✅ 可用，OpenAI-compatible |
| **LLMRouter** | llm_router.py | ⚠️ 被 MBOSCore 使用，几乎不用 |
| **内置 TokenPool** | token_pool.py (Mother内) | ⚠️ 与独立 TokenPool 服务功能重复 |
| **Provider 管理** | providers.py | ⚠️ 数据库有表但几乎不被调用 |
| **Tool 执行** | tools.py | ✅ 可用，25 个内置工具 |
| **Skill 执行** | skills.py | ✅ 可用，14 GitHub + SSH + 10 占位 |
| **Tool 运行时(旧)** | tool_runtime.py | ⚠️ MBOSCore 用，几乎不用 |
| **Session Pipeline** | pipeline.py | ✅ 可用，close_session |
| **MBOSCore** | mbos_core.py | ⚠️ 早期原型，不维护 |
| **Gateway Agent** | gateway_agent.py | ✅ 可用，thin forwarder |
| **Output Sanitizer** | output_sanitizer.py | ⚠️ 被 MBOSCore 用 |
| **数据库** | db.py + models.py | ✅ 可用，SQLite+WAL+FTS5 |
| **API** | api.py | ✅ 可用，18 个端点 |
| **Capabilities** | capabilities/ | ⚠️ 数据模型定义，未被使用 |

## 缺什么

| 缺失项 | 重要性 | 说明 |
|--------|--------|------|
| **统一的 LLM Provider 层** | 🔴 高 | 当前 4 条调用路径各自为政 |
| **TokenPool HTTP 客户端** | 🔴 高 | Mother 应通过 API 调 TokenPool，而非读文件 |
| **消息总线/事件系统** | 🟡 中 | Mother ↔ TokenPool ↔ Panel 之间无实时通信 |
| **Session 持久化** | 🟡 中 | WorkingMemory 纯内存，重启丢失 |
| **工具注册中心** | 🟡 中 | 工具定义散落在 4 个文件中 |
| **配置中心** | 🟢 低 | 环境变量 + JSON 文件 + 数据库混用 |
| **日志/可观测性** | 🟢 低 | 仅 print 和 logging，无结构化日志 |
| **测试** | 🟢 低 | 无任何测试代码 |

## 保留什么

| 保留项 | 理由 |
|--------|------|
| MotherRuntime | 核心 agent loop，设计合理 |
| WorkingMemory | 会话上下文管理，可行 |
| MemoryRepo + 双路召回 | 长期记忆系统，核心能力 |
| tools.py (执行引擎) | 工具执行，重构 dispatch 即可 |
| skills.py (GitHub/SSH) | 高级技能，有实际价值 |
| pipeline.py | 会话关闭流程 |
| gateway_agent.py | 多渠道消息转发 |
| 数据库模型 (5 表) | 设计清晰 |
| FTS5 全文索引 | SQLite 内置，无需额外依赖 |
| API 端点 (api.py 核心) | 功能完整 |

## 删除什么

| 删除项 | 理由 |
|--------|------|
| agent.py | 与 MotherRuntime 重复 |
| llm_router.py | 与 LLMClient 重复，MBOSCore 不用 |
| tool_runtime.py | MBOSCore 工具运行时，可合并入 tools.py |
| mbos_core.py | 早期原型 |
| output_sanitizer.py | 仅 MBOSCore 使用 |
| capabilities/ | 仅数据模型，无消费者 |
| providers.py | 功能被 TokenPool 覆盖 |
| Mother 内置的 token_pool.py | 改为通过 HTTP API 调 TokenPool 服务 |
| admin/ 中 14 个 .bak 文件 | 备份文件 |
| admin/ 中重复的 HTML 文件 | panel_test.html, panel_v2.html 等 |

## 迁移什么

| 迁移项 | 从 | 到 |
|--------|----|----|
| LLM 调用 | Mother 直接读 TokenPool 文件 | Mother 通过 HTTP API 调 TokenPool |
| Provider 管理 | providers.py (数据库) | TokenPool keys 表 |
| 工具定义 | 散落在 system prompt + tools.py + skills.py | 统一的 ToolRegistry |
| Admin JSON 数据 | admin.json, users.json, stats.json | 合并到 SQLite |
| 心跳数据 | heartbeat_logs JSON 文件 | 考虑统一到 TokenPool 或 SQLite |

## 以后新增什么

| 新增项 | 优先级 | 说明 |
|--------|--------|------|
| **ProviderManager** | P0 | 统一的 LLM 调用入口，封装 TokenPool HTTP 客户端 + 本地 Key fallback |
| **ToolRegistry** | P1 | 统一的工具注册/发现/执行框架 |
| **EventBus** | P2 | 简单的进程内事件系统 (Mother ↔ Panel 通知) |
| **ConfigManager** | P2 | 统一的配置管理（环境变量 + 数据库） |
| **SessionStore** | P2 | WorkingMemory 持久化能力 |
| **Structured Logging** | P3 | JSON 格式日志 |
| **Health/Metrics 端点** | P3 | Prometheus 兼容指标 |

## 改造优先级排序

```
P0 (必须):  统一 LLM Provider 层，删除重复代码
P1 (重要):  统一工具注册、TokenPool HTTP 集成
P2 (改进):  EventBus、配置中心、Session 持久化
P3 (增强):  日志、指标、测试
```

## 改造后目标架构

```
Mother (FastAPI, 单一进程)
├── core/
│   ├── runtime.py        ← MotherRuntime (保留+增强)
│   ├── memory.py         ← MemoryRepo (保留)
│   ├── pipeline.py       ← close_session (保留)
│   └── event_bus.py      ← 新增：进程内事件
├── llm/
│   └── provider.py       ← 新增：统一 Provider 层 (封装 TokenPool HTTP)
├── tools/
│   ├── registry.py       ← 新增：统一工具注册
│   ├── builtin.py        ← 迁移：tools.py 内置工具
│   └── skills.py         ← 保留：GitHub/SSH 技能
├── gateway/
│   ├── agent.py          ← 保留：gateway_agent
│   └── adapters/         ← 保留：QQ/微信/Web
├── api/
│   ├── sessions.py       ← 保留：会话 CRUD
│   ├── agent.py          ← 保留：agent 端点
│   └── admin.py          ← 迁移：控制面板 API
├── db/
│   ├── engine.py         ← 保留：db.py
│   └── models.py         ← 保留 + 新增 admin 表
└── main.py               ← 精简入口
```

## 禁止事项 (重申)

以下在本阶段**禁止**：
- ❌ 新增 Runtime（已有 MotherRuntime）
- ❌ 新增 Memory（已有 MemoryRepo）
- ❌ 新增 Gateway（已有 gateway_agent）
- ❌ 新增 EventBus（先分析，以后再建）
- ❌ 新增 Worker
- ❌ 新增 Capability
- ❌ 新增 Compute
- ❌ 新增 Planner
- ❌ 新增 Scheduler
- ❌ 修改代码（只分析）
- ❌ 开发 Mother 新功能
- ❌ 重构现有代码
- ❌ 新增模块
