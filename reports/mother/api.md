# Mother API 分析

## 作用

API 层提供 REST API 和 Gateway 入口。Mother 的 FastAPI 应用挂在 `main.py`，API 路由分散在 7 个文件中。

## 当前实现

### 主入口（main.py）
```
FastAPI app (version 0.4.0)
├── CORS 中间件（allow all origins）
├── track_users 中间件（用户调用追踪）
├── lifespan：init_db() + 启动微信 Bot
└── 7 个路由模块
```

### 路由模块总览

| 文件 | Prefix | 功能 |
|------|--------|------|
| app/api.py | `/` | 会话 CRUD、Agent、工具、搜索、客户端版本 |
| app/admin/router.py | `/admin` | 登录、统计、用户管理、Token池管理 |
| app/admin/admin_api.py | `/admin` | 管理面板 API |
| app/admin/bridge_manager.py | `/bridge` | MiClaw Bridge 管理 |
| app/admin/debug_api_v2.py | `/debug` | 调试/设备命令 |
| app/admin/version_api.py | `/admin` | 版本管理 |
| app/admin/upload.py | - | 文件上传 |
| app/admin/extra.py | `/admin` | Bugs/Features 反馈 |

### api.py 核心端点（18 个）

**会话管理**：
- `POST /sessions` — 创建会话（v6 单会话模式，按 code 复用）
- `POST /sessions/{sid}/messages` — 添加消息 + JSONL 转录
- `POST /sessions/{sid}/close` — 关闭会话（LLM 摘要 → 记忆写入）
- `GET /sessions/{sid}/messages` — 列出消息
- `GET /search` — FTS + 关键词搜索

**Agent**：
- `POST /agent/run` — 执行 agent loop
- `GET /agent/status` — 当前 agent 状态

**工具**：
- `GET /tools` — 列出工具（支持 category/tag 过滤）
- `GET /tools/search` — 搜索工具
- `GET /tools/{tool_id}` — 工具详情
- `POST /tools/execute` — 执行工具

**其他**：
- `GET /providers` — LLM Provider 列表
- `GET /client/version` — 客户端版本
- `GET /client/linux/status` — Linux 环境状态
- `GET /api/mother/uploads/{code}` — 设备上传文件列表（定义两次，重复代码）

### Gateway 入口（main.py 内联）
- `POST /gateway/web/chat` — Web 聊天
- `GET /gateway/wechat/link` — 微信扫码登录
- `GET /gateway/wechat/qr` — 微信二维码页面
- `GET /gateway/wechat/poll` — 扫码状态轮询
- `POST /gateway/wechat/login` — 微信登录确认
- `GET /gateway/wechat/accounts` — 微信账号列表

### 管理面板端点（admin/）
- `POST /admin/api/login` / `logout` — 登录认证
- `GET /admin/api/overview` — 统计概览
- `GET /admin/api/users` — 用户列表
- `GET /admin/api/token-pool` — Token池状态
- `GET /admin/api/miclaw-instances` — MiClaw实例列表
- 静态页面：`/`, `/admin`, `/admin2`, `/admin/login`
- Hotfix 文件服务：`/hotfix/latest.json`, `/hotfix/{filename}`

## 存在问题

1. **路由分散**：7 个路由文件，部分功能重叠（如 admin_api.py 和 router.py 的 prefix 都是 /admin）
2. **端点定义重复**：`/api/mother/uploads/{code}` 在 api.py 中定义了两次（完全相同的代码）
3. **Gateway 端点内联在 main.py**：WebChat、微信登录等逻辑嵌在 main.py 中，应独立为 GatewayRouter
4. **CORS allow all**：`allow_origins=["*"]` 不安全
5. **无 API 版本管理**：`/v1/` 路径在中间件中识别但无实际路由
6. **管理面板 HTML 路径硬编码**：`/opt/mbclaw/admin-panel/app/admin/panel_one.html`
7. **健康检查过于简单**：只检查 db 文件是否存在，不检查连接
8. **`record_session_created` 在 /agent/run 中被调用但未 import**

## 建议

1. 合并 admin/router.py 和 admin/admin_api.py
2. 提取 Gateway 端点到独立模块
3. 删除重复的 `/api/mother/uploads/{code}` 定义
4. 限制 CORS origins
5. 所有路径使用配置而非硬编码

## 以后是否保留

**保留，但需要整理**：
- api.py 核心端点 → 保留
- admin 路由 → 合并整理
- Gateway 端点 → 提取为独立模块
- main.py → 精简为纯入口文件
