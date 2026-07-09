# MBclaw 三大工程关系分析

## 整体架构关系图

```
┌──────────────────────────────────────────────────────────────────┐
│                        用户/设备                                  │
│                    (Android App + QQ/微信)                         │
└──────┬──────────────┬──────────────┬─────────────────────────────┘
       │              │              │
       │ 心跳+命令     │ QQ/微信消息   │ Web聊天
       ▼              ▼              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Mother (母体)                                  │
│              FastAPI 主进程 (端口 80)                              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │ Control Panel│  │ MotherRuntime│  │ Gateway (QQ/微信/Web)  │   │
│  │ (管理面板)   │  │ (Agent Loop) │  │                        │   │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬───────────┘   │
│         │                 │                        │               │
│         │   SQLite DB     │   工具执行               │               │
│         │   (Mother)      │   (tools/skills)        │               │
│         ▼                 ▼                        ▼               │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │              JSON 文件存储 (heartbeat_logs, admin, stats) │     │
│  └──────────────────────────────────────────────────────────┘     │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       │ LLM 调用 (4 种路径)
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                    TokenPool (工具池)                              │
│              FastAPI 独立进程 (端口 8100)                           │
│  ┌──────────┐  ┌───────────┐  ┌───────────┐  ┌───────────────┐   │
│  │ Registry │  │ Scheduler │  │  Caller   │  │ Health/Metrics│   │
│  │ (Key管理)│  │ (调度路由) │  │ (LLM调用) │  │ (健康/指标)   │   │
│  └──────────┘  └───────────┘  └───────────┘  └───────────────┘   │
│                                                                   │
│  SQLite DB: pool.db + ratelimit.db                                │
└──────────────────────────────┬────────────────────────────────────┘
                               │
                               │ 转发到上游 LLM
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│              上游 LLM Provider                                     │
│  OpenAI | Anthropic | DeepSeek | 智谱 | 通义千问 | MiClaw Bridge  │
└──────────────────────────────────────────────────────────────────┘
```

## 一、Mother 如何调用 TokenPool？

Mother 有 **4 条不同路径** 调用 TokenPool：

### 路径 1：MotherRuntime._build_candidates()
```python
# mother_runtime.py:281
from app.token_pool import get_pool
pool = get_pool()
# 直接遍历 pool.keys，按 provider 优先级选择
```
- **方式**：直接导入 Mother 内置的 TokenPool 模块（app/token_pool.py）
- **特点**：不调用 TokenPool 服务（端口 8100），而是读取共享文件（heartbeat_logs）
- **问题**：绕过了 TokenPool 的 Scheduler/GuardRail/故障转移

### 路径 2：LLMClient fallback
```python
# llm.py:61-69
from app.token_pool import get_pool
best = get_pool().get_best_for_llm()
```
- **方式**：同路径 1，使用 Mother 内置 TokenPool 模块
- **特点**：只在环境变量未配置时作为 fallback

### 路径 3：LLMRouter._call_via_tokenpool()
```python
# llm_router.py:28
from app.token_pool import get_pool
pool = get_pool()
```
- **方式**：同路径 1
- **特点**：被 MBOSCore 使用，几乎不执行

### 路径 4：不通过 HTTP API
Mother **从未通过 HTTP 调用 TokenPool 服务**（`http://xxx:8100`）。TokenPool 作为独立服务部署但 Mother 不用它。

## 二、控制面板如何调用 Mother？

控制面板是 Mother 进程的一部分（共用 FastAPI app），所以是**进程内调用**：

### 管理 API 调用 Mother 功能
```
admin/router.py → /admin/api/token-pool
    ↓ 读取 heartbeat_logs 文件（与 Mother 共享）
    ↓ 不经过 TokenPool 服务

admin/router.py → /admin/api/overview
    ↓ 读取 users.json / stats.json（与 Mother API 共享）
    ↓ 读取 heartbeat_logs

admin/debug_api_v2.py → 心跳处理
    ↓ 保存到 heartbeat_logs/mb-*.json
    ↓ 转发到 TokenPool: http://127.0.0.1:8100/api/heartbeat
```

### TokenPool 管理页面的特殊路径
```python
# admin/router.py:269-275
def _tp_req(path):
    req = _ur.Request(f"http://8.147.69.152:8100{path}", ...)
```
控制面板的 Token 测试功能**直接调 TokenPool HTTP API**（硬编码 IP）。

## 三、TokenPool 如何通知 Mother？

**当前无通知机制**。两者的交互方式：

### TokenPool → Mother：无直接通知
- TokenPool 是独立的 FastAPI 服务
- Mother 不订阅 TokenPool 的任何事件
- 如果 Key 状态变化，Mother 只有在下次调用时才会发现

### 数据共享方式：文件系统
```
heartbeat_logs/mb-*.json  ← Mother (debug_api_v2.py) 写入
                          ← TokenPool (registry.py) 读取
                          ← 控制面板 (admin/router.py) 读取

/var/lib/mbclaw/miclaw_instances.json  ← Mother (bridge_manager.py) 写入
                                       ← TokenPool 不读取 (有自己的 miclaw_accounts 表)
```

## 四、Mother 如何通知控制面板？

**无实时通知**。控制面板的所有数据通过以下方式刷新：
- 前端定时轮询 API
- 页面加载时拉取最新数据

## 五、哪些 API 已经存在？

### Mother 核心 API（api.py）
- 会话 CRUD、消息、搜索、Agent、工具管理、Provider、客户端版本

### 控制面板 API（admin/）
- 登录认证、概览统计、用户管理、设备管理、调试命令、版本管理、下载统计、Bugs/Features

### TokenPool API（routes/）
- Key CRUD、统计、心跳、代理转发、MiClaw 账号池、售出 Key、免费 Key、用户共享 Key

## 六、哪些重复？

| 功能 | Mother 中有 | TokenPool 中有 | 控制面板中有 |
|------|-----------|--------------|-----------|
| Token/Key 管理 | app/token_pool.py | routes/keys.py + registry.py | admin/router.py (读取heartbeat) |
| Key 测试 | TokenPool.test_key() | routes/user_stats.py (probe) | admin/router.py (调TokenPool) |
| LLM 调用 | 4 条路径 | call_with_fallback() | - |
| 设备管理 | debug_api_v2.py | - | admin/router.py (读heartbeat) |
| 统计 | stats.json | call_log 表 | stats.json |
| Provider 管理 | providers.py + models.py | registry.py (keys表) | keys.json |

## 七、哪些需要删除？

| 项目 | 理由 |
|------|------|
| Mother 的 app/token_pool.py | 应通过 HTTP API 调 TokenPool，不直接读文件 |
| Mother 的 app/llm_router.py | MBOSCore 不使用，LLMRouter 功能与 LLMClient 重复 |
| Mother 的 app/agent.py | MotherAgent 基本空壳，agent_run 与 MotherRuntime 重复 |
| Mother 的 app/tool_runtime.py | MBOSCore 工具运行时，已被 tools.py 覆盖 |
| Mother 的 app/mbos_core.py | MBOSCore 是早期原型，未被实际使用 |
| 控制面板 admin/ 中的 .bak 文件 | 备份文件，14 个 .bak/.old 文件应清理 |
| 控制面板 admin/ 中的重复 HTML | panel.html, panel_v2.html, panel_test.html 等多个版本 |

## 八、当前架构核心问题

1. **Mother 内置了一个 TokenPool 副本**（app/token_pool.py），但另有独立的 TokenPool 服务（端口 8100），两者不互通
2. **控制面板是 Mother 的一部分**（同一进程），不是独立服务
3. **三套数据存储**：Mother SQLite + 控制面板 JSON + TokenPool SQLite，数据分散
4. **无消息总线/事件机制**：三个系统间的通信全靠文件系统轮询
