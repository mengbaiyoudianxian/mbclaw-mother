# 03 — Control Panel 架构评审

> 评审人：MBclaw 高级架构师
> 日期：2026-07-09
> 状态：Phase 0 Architecture Freeze（只读分析）

---

## 一、工程概况

Control Panel 是 MBclaw 的统一 Web 管理系统，但不是独立服务——它运行在 Mother 的 FastAPI 进程中。

### 定位

```
Mother (FastAPI 进程)
├── MotherRuntime (Agent Loop)
├── Gateway (QQ/微信/Web 入口)
├── Control Panel (管理面板)  ← 同一进程
└── TokenPool 客户端 (内置副本)
```

### 文件统计

```
admin/ 目录 34 个文件
├── 有效 Python: 9 个 (router, bridge_manager, debug_api_v2, admin_api, extra, version_api, upload, collect_simple, __init__)
├── 有效前端:   5 个 (panel_one.html, panel.js, panel_auth.js, miclaw_login.html, bridge_login.html)
├── 废弃 .bak:  5 个
├── 重复 HTML:  10 个 (panel.html, panel_v2.html, panel_test.html, panel_min.html, ...)
├── 废弃模块:   5 个 (main.py, static_index.py, new_admin_html.py, server_collector.py, token_pool.py)
└── 文档:       1 个 (analysis.md)
```

---

## 二、页面结构

### 页面关系图

```
                    ┌──────────────┐
                    │  登录页       │
                    │  /admin/login │
                    └──────┬───────┘
                           │ POST /admin/api/login
                           ▼
                    ┌──────────────┐
                    │  Dashboard   │  ← 默认首页
                    │  /admin2     │
                    └──┬──┬──┬─────┘
                       │  │  │
        ┌──────────────┘  │  └──────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  设备管理     │  │  Token Pool  │  │  MiClaw      │
│  用户列表     │  │  Key 管理    │  │  Bridge      │
│  心跳状态     │  │  测试/检测   │  │  实例/代理   │
│  调试命令     │  │              │  │              │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                  │
       ▼                 ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Bugs/       │  │  文件上传     │  │  Settings    │
│  Features    │  │  /upload     │  │  密码/版本   │
│  反馈管理     │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

### 功能清单

| 页面 | 功能 | 后端路由 |
|------|------|---------|
| 登录 | 账号密码认证 | admin/router.py |
| Dashboard | 总请求/Token/用户/在线设备/运行时间 | admin/router.py + admin_api.py |
| 设备管理 | 设备列表、权限、收集开关、封禁 | debug_api_v2.py |
| Token Pool | Key 列表、单测/全量检测 | admin/router.py (调 TokenPool API) |
| MiClaw | 实例列表、登录状态、销毁/暂停 | bridge_manager.py |
| Bugs | Bug 反馈管理 | admin/router.py |
| Features | 功能请求管理 | admin/router.py |
| 上传 | 文件上传中转站 | upload.py |
| Settings | 改密码、版本管理 | admin/router.py + version_api.py |

---

## 三、API 调用关系

### 控制面板 → Mother (进程内调用)

```
Dashboard:
  GET /admin/api/overview
    ├── 读 stats.json (请求统计)
    ├── 读 users.json (用户列表)
    ├── 读 keys.json (Provider 配置)
    └── 扫描 heartbeat_logs/ (在线设备)

设备管理:
  GET /admin/client/debug/devices     → 扫描 heartbeat_logs/
  POST /admin/client/debug/send       → 写 pending_commands.json

服务器状态:
  GET /api/admin/metrics              → /proc/meminfo, /proc/net/dev, statvfs
```

### 控制面板 → TokenPool (HTTP 调用)

```
Token Key 测试:
  POST /admin/api/token-pool/test-key
    └── _tp_req("http://8.147.69.152:8100/api/shared-keys/legacy/test-key?code=...")

全量检测:
  POST /admin/api/token-pool/test-all
    └── _tp_req("http://8.147.69.152:8100/api/shared-keys/probe-all")
```

**关键问题**：TokenPool 地址硬编码为 `http://8.147.69.152:8100`。

### 控制面板 → MiClaw Bridge (HTTP 代理)

```
MiClaw 实例:
  POST /bridge/miclaw/apply           → 创建实例记录
  POST /bridge/miclaw/login/{id}      → 验证凭证(call MiClaw API)
  GET  /bridge/miclaw/status          → 轮询登录状态

LLM 代理:
  ANY  /bridge/miclaw/v1/{path}       → 透传到 MiClaw Bridge
  ANY  /bridge/miclaw/{path}          → 透传到 MiClaw Bridge (重复!)
```

---

## 四、Mother 对接关系

```
控制面板 ──进程内──> Mother
    │
    ├── 共享数据库: mbclaw.db (SQLite, 同一文件)
    ├── 共享文件:   heartbeat_logs/ (设备心跳)
    ├── 共享文件:   users.json, stats.json (统计)
    ├── 共享模块:   app.memory, app.tools, app.llm
    └── 共享配置:   MBCLAW_DATA, MBCLAW_DB_PATH
```

**特点**：控制面板和 Mother 是同一进程的两个「视图」（admin view vs runtime view）。

---

## 五、TokenPool 对接关系

```
控制面板 ──HTTP──> TokenPool (端口 8100)
    │
    ├── Key 测试: POST /api/shared-keys/legacy/test-key
    ├── 全量检测: POST /api/shared-keys/probe-all
    └── Token 列表: GET /api/shared-keys/legacy/tokens
```

**但实际 Token 列表页面读取的是 heartbeat_logs/，不调 TokenPool API。**

---

## 六、权限体系

### 认证模型

```
单用户 + Cookie Session

登录:
  SHA256(salt + password) → 比对 admin.json
  生成 token: secrets.token_urlsafe(32)
  Set-Cookie: mb_admin={token}; HttpOnly; SameSite=Lax; Max-Age=604800

鉴权:
  require_admin(mb_admin: Cookie)
    └── _check_session(sid) → 查 admin_sessions.json
```

### 鉴权覆盖

| API 路径 | 鉴权 | 风险评估 |
|----------|------|---------|
| /admin/api/* | ✅ Cookie | 安全 |
| /api/admin/* | ✅ Cookie | 安全 |
| /bridge/miclaw/* | ❌ 无鉴权 | 🔴 任何人可创建实例、代理LLM |
| /admin/client/debug/* | ❌ 无鉴权 | 🟡 设备直接调用 |
| /upload | ⚠️ URL Token | 🟡 Token 写死 |
| /gateway/wechat/* | ❌ 无鉴权 | 🟢 公开入口合理 |
| /health | ❌ 无鉴权 | 🟢 健康检查合理 |

---

## 七、数据来源

### 数据源分散

```
控制面板数据流:

┌─────────────────────────────────────────────────────────┐
│                    数据消费方 (前端)                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Dashboard 统计 ──── stats.json ──── record_request()   │
│  用户列表      ──── users.json ──── record_user_call()  │
│  在线设备      ──── heartbeat_logs/*.json               │
│  Key 配置      ──── keys.json                           │
│  Token 池      ──── heartbeat_logs/*.json (不是TokenPool!)│
│  下载统计      ──── downloads.json                      │
│  Bugs/Features ──── bugs.json / features.json           │
│  服务器指标    ──── /proc/* (实时读取)                   │
│  MiClaw 实例   ──── miclaw_instances.json               │
│  设备命令      ──── pending_commands.json               │
│  版本配置      ──── version.json                        │
│                                                         │
│  总计: 10+ 个 JSON 文件 + 1 个目录扫描                   │
└─────────────────────────────────────────────────────────┘
```

### 与 Mother SQLite 的重叠

| 数据 | Panel (JSON) | Mother (SQLite) |
|------|-------------|-----------------|
| 会话 | admin_sessions.json | sessions 表 |
| 统计 | stats.json | call_log 表 (TokenPool) |
| 设备 | heartbeat_logs/*.json | 无 |
| 配置 | keys.json, version.json | tools 表, model_profiles 表 |

---

## 八、架构评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 功能完整性 | ⭐⭐⭐⭐ | 管理功能覆盖全面 |
| 代码整洁度 | ⭐⭐ | 大量 .bak、重复 HTML、废弃代码 |
| 数据一致性 | ⭐⭐ | 10+ JSON 文件分散，与 SQLite 并行 |
| 安全性 | ⭐⭐ | 单用户模型可接受，但 Bridge 公开无鉴权 |
| 前端质量 | ⭐⭐ | 纯 JS SPA 无框架，panel.js 数千行 |
| 可维护性 | ⭐ | JSON 文件无 schema，无迁移，无测试 |

### 核心问题

1. **数据存储混乱**：10+ JSON 文件 + SQLite 并行，无统一数据源
2. **TokenPool 集成断裂**：Token 列表读本地文件，Key 测试调远程 HTTP——两条路径
3. **Bridge 公开无鉴权**：任何人可以调用 MiClaw API
4. **前端维护困难**：单文件 SPA，无模块化，无版本管理
