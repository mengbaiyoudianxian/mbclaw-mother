# Control Panel 概览

## 作用

控制面板是 MBclaw 的统一管理系统，提供基于 Web 的管理界面，管理用户、设备、TokenPool、Mother、MiClaw 桥接、文件上传、版本升级、日志统计等功能。

## 技术栈

- **后端**：FastAPI（与 Mother 共用同一进程）
- **前端**：原生 HTML/JS（单页应用，无框架）
- **数据存储**：JSON 文件（admin.json、users.json、stats.json 等）
- **认证**：Cookie-based session（7 天有效期）

## 页面关系图

```
                      ┌─────────────────┐
                      │   登录页         │
                      │  /admin/login    │
                      └────────┬────────┘
                               │ POST /admin/api/login
                               ▼
                      ┌─────────────────┐
                      │   Dashboard     │
                      │   /admin2       │
                      │   (概览)        │
                      └───┬───┬───┬─────┘
                          │   │   │
          ┌───────────────┘   │   └───────────────┐
          ▼                   ▼                   ▼
┌──────────────────┐  ┌──────────────┐  ┌──────────────────┐
│   设备管理        │  │  Token Pool  │  │   MiClaw Bridge  │
│   用户/设备列表   │  │  Key 列表    │  │   实例管理        │
│   心跳/权限/收集  │  │  测试/检测   │  │   登录/状态/销毁   │
└────────┬─────────┘  └──────┬───────┘  └────────┬─────────┘
         │                   │                    │
         ▼                   ▼                    ▼
┌──────────────────┐  ┌──────────────┐  ┌──────────────────┐
│   调试命令        │  │   统计信息    │  │   文件上传        │
│   send/result    │  │   请求/Token  │  │   /upload         │
└──────────────────┘  └──────────────┘  └──────────────────┘
         │
         ▼
┌──────────────────┐
│   Bugs/Features  │
│   反馈管理        │
└──────────────────┘
         │
         ▼
┌──────────────────┐
│   Settings       │
│   密码修改/版本    │
└──────────────────┘
```

## 路由模块组成

| 模块 | 文件 | Prefix | 功能 |
|------|------|--------|------|
| 主入口 | main.py | `/` | 静态页面、健康检查、微信登录 |
| 管理路由 | admin/router.py | `/admin` | 登录认证、概览、用户、TokenPool、Bugs/Features |
| 管理 API | admin/admin_api.py | `/api/admin` | 用户详情、下载统计、服务器指标 |
| 桥接管理 | admin/bridge_manager.py | `/bridge` | MiClaw 实例申请/登录/代理 |
| 调试 API | admin/debug_api_v2.py | `/admin/client/debug` | 心跳、命令下发、设备列表 |
| 版本 API | admin/version_api.py | `/admin/client/version` | 客户端版本检测 |
| 文件上传 | admin/upload.py | `/upload` | 文件上传中转站 |
| 扩展路由 | admin/extra.py | - | 账号同步、工具市场、权限模板 |

## 数据存储

控制面板使用 JSON 文件存储（非 SQLite）：

| 文件 | 用途 |
|------|------|
| admin.json | 管理员账号/密码(hash) |
| users.json | 用户调用记录 |
| stats.json | 请求统计 |
| keys.json | Provider Key 配置 |
| admin_sessions.json | 管理会话 |
| miclaw_instances.json | MiClaw 实例状态 |
| miclaw_blacklist.json | 黑名单 |
| accounts.json | 账号同步数据 |
| shared_tools.json | 共享工具市场 |
| bugs.json / features.json | 反馈管理 |
| version.json | 客户端版本配置 |
| downloads.json | 下载统计 |
| server_status.json | 服务器采集状态 |

## 存在问题

1. **JSON 文件存储无并发安全**：多请求同时写可能数据丢失
2. **前端无框架**：panel_one.html 是单文件 SPA，约数千行 JS，维护困难
3. **认证简单**：单用户 admin，密码哈希用 SHA256 + salt，无 2FA
4. **无 API 鉴权分层**：所有 admin API 用同一个 Cookie 认证
5. **数据与 Mother 的 SQLite 分离**：Heartbeat 数据同时存在于 JSON 文件和 SQLite FTS 中
