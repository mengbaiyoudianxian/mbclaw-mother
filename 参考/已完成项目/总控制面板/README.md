# MBclaw 总控制面板 (Mother Control Panel)

MBOS 母体核心服务 — 多模型智能调度、工具执行、会话管理、QQ Bot 网关。

**版本**: 0.4.0 | **阶段**: Phase 1 — Kernel Foundation (已完成)

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

```bash
# 从模板创建配置文件
cp .env.example .env

# 编辑 .env，填入你的 LLM API Key
# 或使用 Mock 模式（不需 API Key）
```

### 3. 启动

```bash
# Mock 模式（测试用，无需 API Key）
./start.sh --port 8080 --mock

# 生产模式（使用 .env 中的真实 LLM 配置）
./start.sh --port 8080

# 直接使用 uvicorn
MBCLAW_LLM_MOCK=1 uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### 4. 验证

```bash
curl http://localhost:8080/health
# {"db_ok": true, "version": "0.4.0", "service": "MBclaw"}

curl -X POST http://localhost:8080/gateway/web/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'
# {"reply": "[MOCK] 收到: 你好"}
```

---

## 配置说明

### LLM 模型 (必填或使用 Mock)

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MBCLAW_LLM_BASE_URL` | API Base URL | `https://api.openai.com/v1` |
| `MBCLAW_LLM_API_KEY` | API Key | (必填) |
| `MBCLAW_LLM_MODEL` | 模型名称 | `gpt-4o-mini` |
| `MBCLAW_LLM_MOCK` | Mock 模式 (设为 `1`) | 未设置 |

### 存储

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MBCLAW_DB_PATH` | SQLite 数据库路径 | `data/mbclaw.db` |
| `MBCLAW_DATA` | 主数据目录 | `/var/lib/mbclaw` |
| `MBCLAW_UPLOADS` | 文件上传目录 | `/var/lib/mbclaw/uploads` |
| `MBCLAW_UPLOAD_TOKEN` | 上传认证 Token | `mengbai` |

### 外部服务 (可选)

| 变量 | 说明 |
|------|------|
| `GITHUB_TOKEN` | GitHub API 访问令牌 |
| `SSH_PASS` | SSH 密码 |
| `QQ_BOT_APPID` | QQ Bot App ID |
| `QQ_BOT_SECRET` | QQ Bot Secret |
| `OPENAI_API_KEY` | OpenAI API Key (备用 Provider) |
| `MICLAW_BRIDGE_URL` | MiClaw Bridge 地址 |

---

## 架构

```
HTTP Request
  │
  ▼
main.py (FastAPI) ─── /gateway/web/chat, /agent/run, /health, ...
  │
  ▼
gateway_agent.py → Gateway.handle(StandardMessage)
  │
  ▼
MotherRuntime.run()  ←── 核心调度引擎
  │
  ├── Governor.check()        ←── 请求准入 (空消息拦截等)
  ├── Planner.create_plan()   ←── 目标分解
  ├── Memory.query()          ←── 记忆检索
  ├── ContextEngine.build()   ←── System Prompt + 上下文组装
  ├── Scheduler.dispatch()    ←── LLM 调用 (Mock / TokenPool / 直连)
  │     ├── TokenPool.acquire()  (用户贡献 Key 池)
  │     └── LLMClient            (env var 直连，fallback)
  └── Capability.execute()    ←── 工具执行
```

### Phase 1 模块

| 模块 | 目录 | 职责 |
|------|------|------|
| Runtime | `app/runtime/` | 核心调度引擎，run() 单一入口 |
| Gateway | `app/gateway/` | 消息协议标准化 |
| Governor | `app/governor/` | 请求准入与安全策略 |
| Scheduler | `app/scheduler/` | LLM 调用调度 (唯一 HTTP 出口) |
| TokenPool | `app/token_pool/` | LLM Key 资源池 |
| ContextEngine | `app/context/` | System Prompt + 上下文组装 |
| Memory | `app/memory/` | 会话记忆存储与检索 |
| Planner | `app/planner/` | 目标分解为执行步骤 |
| Capability | `app/capability/` | 工具注册与执行 |

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/gateway/web/chat` | Web 聊天 (母体对话) |
| POST | `/agent/run` | Agent 循环执行 |
| GET | `/agent/status` | Agent 会话状态 |
| POST | `/sessions` | 创建会话 |
| POST | `/sessions/{id}/messages` | 添加消息 |
| POST | `/sessions/{id}/close` | 关闭会话 (摘要+记忆) |
| GET | `/sessions/{id}/messages` | 会话消息列表 |
| GET | `/search` | 记忆搜索 |
| GET | `/providers` | LLM Provider 列表 |
| GET | `/tools` | 工具列表 |
| POST | `/tools/execute` | 执行工具 |
| GET | `/client/version` | 客户端版本信息 |

---

## 测试

```bash
# 单元测试
python3 -m pytest app/scheduler/ app/governor/ app/token_pool/ app/context/ app/memory/ app/planner/ app/capability/ app/gateway/

# 集成测试 (Mock 模式)
MBCLAW_LLM_MOCK=1 python3 -c "
from app.runtime import get_runtime
from app.gateway import Gateway, StandardMessage

rt = get_runtime()
gw = Gateway(rt)

# Runtime direct
r = rt.run('你好', session_id=1, max_turns=1)
assert r.success

# Gateway handle
r2 = gw.handle(StandardMessage(content='测试', channel='qq', session_id='1'))
assert r2.success

# Governor deny
r3 = rt.run('', session_id=1, max_turns=1)
assert not r3.success

print('All integration tests passed')
"
```

---

## 已知限制

1. **TokenPool v1 为空**: Phase 1 的 TokenPool 需要手动注册候选 Key。默认使用 `MBCLAW_LLM_*` 环境变量直连 LLM。
2. **Memory v1 为内存存储**: 重启后记忆丢失。后续版本将接入持久化存储。
3. **无认证**: 管理 API 端点未强制认证 (内网部署)。

---

## 部署建议

- **开发/测试**: `./start.sh --mock` (无需 API Key)
- **内网生产**: 配置 `.env` 中的 LLM API Key，supervisor/systemd 管理进程
- **日志**: uvicorn 日志输出到 stdout，建议配合 journald 或 logrotate

### systemd 示例

```ini
[Unit]
Description=MBclaw Mother Control Panel
After=network.target

[Service]
Type=simple
User=mbclaw
WorkingDirectory=/opt/mbclaw/total-control-panel
ExecStart=/opt/mbclaw/total-control-panel/start.sh --port 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
