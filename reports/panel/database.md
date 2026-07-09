# Control Panel 数据库分析

## 概述

控制面板不使用 SQLite，而是使用多个 JSON 文件存储配置和运行时数据。这与 Mother 的 SQLite 数据库是两套独立存储。

## JSON 文件清单

### 认证 & 会话
| 文件 | 结构 | 用途 |
|------|------|------|
| admin.json | {username, salt, hash, created_at} | 管理员密码（SHA256 + salt） |
| admin_sessions.json | {sid: {created_at, expires_at}} | 会话管理（7 天过期） |

### 用户 & 统计
| 文件 | 结构 | 用途 |
|------|------|------|
| users.json | {user_id: {first_seen, last_seen, calls, ip, blocked}} | 用户调用追踪 |
| stats.json | {total_requests, total_tokens_in, errors, daily, providers} | API 调用统计 |

### MiClaw
| 文件 | 结构 | 用途 |
|------|------|------|
| miclaw_instances.json | {app_id: {status, token, user_id, ...}} | MiClaw 实例管理 |
| miclaw_blacklist.json | {ips: [], devices: []} | 黑名单 |

### 配置 & 数据
| 文件 | 结构 | 用途 |
|------|------|------|
| keys.json | {providers: {}} | Provider Key 配置 |
| accounts.json | {qq/wx: {qq, wx, nick}} | 账号同步 |
| shared_tools.json | {tools: []} | 工具市场 |
| version.json | {latest, download_url, changelog} | 客户端版本 |
| downloads.json | {file: {total, today}} | 下载统计 |
| bugs.json | {bugs: []} | Bug 反馈 |
| features.json | {features: []} | Feature 请求 |

### 设备数据
| 目录/文件 | 用途 |
|-----------|------|
| heartbeat_logs/mb-*.json | 设备心跳数据（每个设备一个文件） |
| pending_commands.json | 待下发命令队列 |
| server_status.json | 服务器采集状态 |

## 数据流

```
设备心跳 → heartbeat_logs/mb-{code}.json
              ↓
         admin/router.py 读取 → 概览/设备列表/Token列表
              ↓
         admin/debug_api_v2.py → 转发到 TokenPool (http://127.0.0.1:8100)

管理面板操作 → JSON 文件 (_load/_save)
              ↓
         users.json / stats.json / bugs.json ...
```

## 与 Mother SQLite 的重叠

| 数据 | 控制面板 (JSON) | Mother (SQLite) |
|------|----------------|-----------------|
| 会话 | admin_sessions.json | sessions 表 |
| 调用统计 | stats.json | call_log 表（TokenPool） |
| Provider Key | keys.json | keys 表（TokenPool） |
| 设备数据 | heartbeat_logs/*.json | - |

## 存在问题

1. **两套存储并行，无统一数据源**：心跳数据 JSON + Mother SQLite 各自维护
2. **JSON 文件无并发保护**：_load/_save 无锁，并发写可能丢数据
3. **无 Schema 校验**：JSON 文件结构靠代码约定，无类型约束
4. **文件数量随设备线性增长**：每个设备一个 heartbeat JSON 文件
5. **bugs/features 没有单独的 ID 生成机制**：靠前端提交时带 id
6. **无备份机制**：JSON 文件无 WAL、无定期备份

## 建议

1. 将 admin JSON 数据迁移到 SQLite，统一数据源
2. 高频写入的 heartbeat 数据考虑用队列而非文件轮询
3. 所有 JSON 写操作加 fcntl 文件锁（api.py 中已有 _append_transcript 示范）
