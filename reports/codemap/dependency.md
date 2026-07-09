# CodeMap — MBclaw Mother 代码依赖图

> 自动生成时间: 2026-07-09
> 基于 Phase 0 静态分析

## import 统计

### Mother 核心模块依赖

```
main.py
├── app.api                    (router)
├── app.db                     (init_db)
├── app.admin.router           (admin_router)
├── app.admin.extra            (admin_extra_router)
├── app.admin.upload           (admin_upload_router)
├── app.admin.version_api      (version_router)
├── app.admin.bridge_manager   (bridge_router)
├── app.admin.debug_api_v2     (debug_router)
├── app.admin.admin_api        (admin_api_router)
└── app.gateway.adapters.wechat (WechatAdapter)

mother_runtime.py (335行)
├── re, time, httpx
├── app.memory.MemoryRepo      (外部, 仅当 db_factory 存在)
├── app.token_pool.get_pool    (外部, 应改为 HTTP)
├── app.skills.execute_skill   (外部)
└── app.tools.execute          (外部)

api.py (368行)
├── app.db.get_db              (FastAPI Depends)
├── app.llm.LLMClient, get_llm
├── app.memory.MemoryRepo
├── app.models.Message, Session
├── app.pipeline.close_session
├── app.agent.agent_run
├── app.providers.list_providers
├── app.tools.execute, list_tools, search_tools
└── fcntl, json, os, datetime

tools.py (428行)
├── app.models.Tool
├── app.memory.MemoryRepo      (search_memory)
├── app.admin.debug_api_v2     (device commands, 紧耦合!)
└── subprocess, json, os, jieba

skills.py (~305行)
├── httpx
├── subprocess
└── os, json, base64
    (独立模块, 无 MBclaw 内部依赖)

llm.py (147行)
├── app.token_pool.get_pool    (fallback, 应删除)
└── httpx, json, os, pydantic

pipeline.py (75行)
├── app.llm.LLMClient
├── app.memory.MemoryRepo
├── app.models.Message, Session
└── jieba.analyse

gateway_agent.py (23行)
└── app.mother_runtime.get_runtime
    (thin forwarder)

memory.py (193行)
├── app.models (5个ORM类)
├── jieba
└── sqlalchemy, pydantic

db.py (61行)
└── sqlalchemy (create_engine, sessionmaker)

models.py (112行)
└── app.db.Base
```

## 类统计

| 文件 | 类 | 行数 |
|------|-----|------|
| mother_runtime.py | WorkingMemory, MotherRuntime | 335 |
| memory.py | MemoryHit, MemoryRepo | 193 |
| llm.py | LLMError, LLMOutput, LLMClient | 147 |
| models.py | Session, Message, Summary, Keyword, Experience, Tool, ModelProfile | 112 |
| tools.py | (module-level functions) | 428 |
| skills.py | (module-level functions) | 305 |
| pipeline.py | (module-level functions) | 75 |
| agent.py | StandardMessage, MotherAgent | 204 |
| mbos_core.py | MBOSCore (废弃) | 77 |
| tool_runtime.py | ToolRuntime (废弃) | 80 |
| llm_router.py | LLMRouter (废弃) | 50 |
| token_pool.py | PoolKey, TokenPool | 161 |
| output_sanitizer.py | OutputSanitizer (废弃) | 16 |

## API 统计 (api.py)

| 方法 | 数量 |
|------|------|
| POST | 5 |
| GET | 12 |
| 重复定义 | 1 (/api/mother/uploads/{code} 定义了两次) |

## 工具统计

| 类别 | 数量 | 位置 |
|------|------|------|
| 内置工具 (tool) | 25 | tools.py BUILTIN_TOOLS |
| GitHub 技能 (skill) | 14 | skills.py |
| SSH 技能 (skill) | 1 | skills.py |
| API 占位 (skill) | 10 | skills.py |
| LLM Prompt 技能 | 21 | skills.py LLM_SKILL_PROMPTS |
| 设备工具 | 30+ | tools.py DEVICE_TOOL_NAMES |
| MBOSCore 工具 | 3 | tool_runtime.py (废弃) |
| **合计** | **~100+** | 分布在 4 个文件中 |

## 数据库表统计

| 表 | 所属 | 状态 |
|----|------|------|
| sessions | Mother SQLite | ✅ |
| messages | Mother SQLite | ✅ |
| summaries | Mother SQLite | ✅ |
| keywords | Mother SQLite | ✅ |
| experiences | Mother SQLite | ✅ |
| tools | Mother SQLite | ✅ |
| model_profiles | Mother SQLite | ⚠️ 几乎不用 |
| messages_fts | FTS5 虚拟表 | ✅ |
| experiences_fts | FTS5 虚拟表 | ✅ |

## 紧耦合警告

| 耦合点 | 严重程度 |
|--------|---------|
| tools.py → admin.debug_api_v2._debug_commands | 🔴 跨模块直接访问内部变量 |
| mother_runtime.py → app.token_pool.get_pool() | 🔴 绕过 TokenPool 服务 |
| main.py → 内联 Gateway 端点 | 🟡 应独立为 GatewayRouter |
| llm.py → app.token_pool.get_pool() | 🟡 fallback 应走 Scheduler |
| admin/router.py → 硬编码 TokenPool IP | 🟡 应配置化 |
