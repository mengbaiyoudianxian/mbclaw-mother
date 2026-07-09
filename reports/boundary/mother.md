# Mother Runtime Boundary — 模块边界定义

> Phase 0: Architecture Freeze
> 明确哪些属于 Mother，哪些不属于。

## 属于 Mother Runtime

| 模块 | 文件 | 职责 |
|------|------|------|
| Governor | `core/governor.py` | 会话生命周期编排 |
| Planner | `core/planner.py` | 意图分析 + 工具选择 |
| Scheduler | `core/scheduler.py` | LLM Provider 调度 (调 TokenPool HTTP) |
| Context Engine | `core/context_engine.py` | WorkingMemory + Prompt 组装 |
| Pipeline | `core/pipeline.py` | close_session 流程 |
| Memory | `memory/` | 长期记忆 (SQLite + FTS5 + jieba) |
| Capability | `capability/` | 统一工具/技能注册 |
| Gateway | `gateway/` | 多渠道消息适配 (QQ/微信/Web/CLI) |
| Compute | `compute/` | 底层执行 (shell/HTTP/device) |
| DB | `db/` | SQLite 引擎 |
| API | `api/` | REST API (会话/Agent/工具) |
| Event | `event/` | 进程内 EventBus (Phase 4) |
| Config | `config/` | 统一配置管理 (Phase 4) |

## 不属于 Mother Runtime

| 系统 | 归属 | 接口方式 |
|------|------|---------|
| TokenPool | 独立服务 (端口 8100) | HTTP API |
| Control Panel | 同一 FastAPI 进程 (admin/) | 进程内 |
| MiClaw Bridge | 第三方服务 (端口 8765) | HTTP 代理 |
| LLM Provider (OpenAI等) | 上游服务 | 通过 TokenPool |

## Mother 边界接口

### 入站 (Mother 对外提供)
```
POST /sessions                    (创建会话)
POST /sessions/{sid}/messages     (添加消息)
POST /sessions/{sid}/close        (关闭会话)
POST /agent/run                   (Agent 执行)
GET  /search?q=                   (记忆搜索)
GET  /tools                       (工具列表)
POST /tools/execute               (工具执行)
GET  /health                      (健康检查)
```

### 入站 (Gateway 渠道)
```
QQ Bot 消息   → Gateway → StandardMessage → Governor
微信 Bot 消息 → Gateway → StandardMessage → Governor
Web Chat     → Gateway → StandardMessage → Governor
```

### 出站 (Mother 调用外部)
```
Scheduler → POST http://tokenpool:8100/v1/chat/completions
Compute   → subprocess (shell commands)
Compute   → heartbeat_logs/ (device commands)
Memory    → SQLite (mbclaw.db)
```

## 明确不属于 Mother 的功能

| 功能 | 归属 | 原因 |
|------|------|------|
| Key 加密存储 | TokenPool | 安全管理应由 TokenPool 集中处理 |
| Provider 评分 | TokenPool | 评分是调度的一部分 |
| 速率限制 | TokenPool | 限流在代理层统一控制 |
| 计费 | TokenPool | 商业化功能 |
| 管理面板 UI | Control Panel | 独立前端 |
| 设备心跳管理 | admin/debug_api_v2.py | 暂留 Mother，Phase 3 评估迁移 |
| APK 下载 | admin/upload.py | 独立功能 |
| 文件上传 | admin/upload.py | 独立功能 |
