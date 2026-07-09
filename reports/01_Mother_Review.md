# 01 — Mother Runtime 架构评审

> 评审人：MBclaw 高级架构师
> 日期：2026-07-09
> 状态：Phase 0 Architecture Freeze（只读分析）

---

## 一、工程概况

Mother 是 MBclaw 的核心 Runtime，运行在 FastAPI 单进程中，同时承载：

| 子系统 | 定位 | 状态 |
|--------|------|------|
| MotherRuntime | 核心 Agent Loop | ✅ 生产可用 |
| MemoryRepo | 长期记忆系统 | ✅ 生产可用 |
| Gateway | 多渠道消息入口 | ✅ 生产可用 |
| Control Panel | 管理面板 | ✅ 生产可用 |
| MBOSCore | 早期原型 | ❌ 废弃 |

### 文件统计

```
总控制面板/app/ 共 103 个文件
├── 有效代码: ~45 个 Python 文件
├── 废弃/重复: ~25 个 (.bak, .broken, 重复HTML/JS)
├── 前端文件: ~10 个 HTML/JS
├── SQL: 1 个 (fts.sql)
└── 管理面板嵌入: ~10 个
```

---

## 二、Runtime 如何工作

### 核心类层次

```
main.py (FastAPI 入口)
    │
    ├── lifespan 启动
    │   ├── init_db() — 建表 + FTS5
    │   └── 启动微信 Bot
    │
    ├── /gateway/web/chat  → gateway_agent.handle_gateway_agent()
    │   └── MotherRuntime.run(msg, session_id)
    │
    ├── POST /agent/run    → agent_run() (旧，基本不用)
    │
    └── /admin/*           → 控制面板路由
```

### Agent Loop 完整流程

```
用户消息 (QQ/微信/Web)
    │
    ▼
gateway_agent.handle_gateway_agent(msg, code)
    │
    │  sid = hash(f"gateway:{code}") % 100000
    ▼
MotherRuntime.run(message, session_id, max_turns=5)
    │
    ├── 1. 获取/创建 WorkingMemory (per session_id)
    │       ├── 首次: 注入 SYSTEM_PROMPT (42 技能 + 14 工具)
    │       └── 已存在: 复用内存上下文
    │
    ├── 2. 添加用户消息到 WorkingMemory
    │
    ├── 3. Memory 注入 (MemoryRepo.query)
    │       └── FTS5 + jieba 双路召回 top-3
    │
    ├── 4. Agent Loop (最多 5 轮)
    │   │
    │   └── for turn in range(max_turns):
    │       │
    │       ├── 4a. _build_candidates()
    │       │   └── 从 TokenPool (app/token_pool.py) 按优先级获取 Key 列表
    │       │       优先级: custom > zhipu > deepseek-cn > miclaw-bridge
    │       │
    │       ├── 4b. LLM 调用 (httpx POST /chat/completions)
    │       │   └── 遍历 candidates[:4]，成功则 break
    │       │
    │       ├── 4c. 解析输出
    │       │   ├── TOOL_RE: <tool>名称</tool><content>参数</content>
    │       │   ├── THINK_RE: <thinking>内容</thinking>
    │       │   └── clean = 去除标签后的纯文本
    │       │
    │       ├── 4d. 无工具 → final_reply = clean → break
    │       │
    │       └── 4e. 有工具 → _execute_tool()
    │           ├── github_* / ssh_exec → skills.execute_skill()
    │           ├── 10 个 API 占位 → skills.api_placeholder()
    │           └── 其他 → tools.execute()
    │
    ├── 5. 返回 {reply, turns, tool_calls}
    │
    └── gateway_agent 清理 Markdown 格式后返回
```

### WorkingMemory 压缩策略

```
total_tokens() = len(all_content) // 4  (粗略估算)

当 total_tokens > limit * 0.80:
    ├── 截断前半消息
    ├── 生成历史摘要: " | ".join(最后3条前80字符)
    └── 插入摘要消息到消息列表头部
```

---

## 三、Memory 如何工作

### 数据模型 (5 表)

```
sessions ──1:N──> messages ──trigger──> messages_fts (FTS5)
    │
    └──1:1──> summaries
    └──1:N──> keywords (jieba 分词)
    └──1:N──> experiences (经验沉淀)
              └──trigger──> experiences_fts (FTS5)
```

### 写入流程 (Session Close)

```
POST /sessions/{sid}/close
    │
    ▼
pipeline.close_session()
    │
    ├── 1. 加载全部 Message
    ├── 2. LLM 摘要 → LLMOutput {summary, keywords, experiences}
    ├── 3. jieba TF-IDF 关键词 (topK=10)
    │       └── 与 LLM 关键词合并: LLM权重1.0, jieba权重0.5
    ├── 4. MemoryRepo.write_session_memory()
    │       ├── 替换 Summary (删除旧+插入新)
    │       ├── 替换 Keywords
    │       └── 追加 Experiences (≤5)
    └── 5. session.status = "closed"
```

### 检索流程 (双路召回)

```
MemoryRepo.query(q, top_n=3)
    │
    ├── A 路: FTS5 全文检索 (权重 0.6)
    │   └── SELECT ... FROM messages_fts WHERE MATCH :q
    │
    ├── B 路: jieba 关键词匹配 (权重 0.4)
    │   └── SELECT ... FROM keywords WHERE keyword IN (tokens)
    │
    └── 合并: score = 0.6×fts_score + 0.4×kw_score → sort → top_n
```

### 经验检索

```
MemoryRepo.query_experiences(q)
    │
    ├── FTS5 搜索 experiences_fts
    ├── kind-priority: failure(1.0) > lesson(0.8) > success(0.5)
    ├── recency bonus = log(recall_count + 1)
    ├── 分数 = 0.7×fts + 0.3×bonus
    └── 自动更新 recall_count
```

### 归档

```
Experience 总数 > 1000 → 最旧的写入 JSONL 归档 → 从 DB 删除
```

---

## 四、Tool 如何调用

### 三套工具系统

| 系统 | 文件 | 工具数 | 状态 |
|------|------|--------|------|
| tools.py | app/tools.py | 25 内置 | ✅ 主力 |
| skills.py | app/skills.py | 14 GitHub + 1 SSH + 10 占位 | ✅ 高级技能 |
| tool_runtime.py | app/tool_runtime.py | 3 (shell/system/read) | ❌ 废弃 |

### 调度路由

```
_execute_tool(name, arg)  (mother_runtime.py:299)
    │
    ├── name.startswith("github_") or name == "ssh_exec"
    │   └── skills.execute_skill(name, arg)
    │       ├── github_search_code, github_list_repos, ...
    │       ├── github_create_pr, github_pr_review, ...
    │       └── ssh_exec(host, cmd, user, port)
    │
    ├── name in (gitlab_api, bitbucket_api, ...) 10个
    │   └── skills.api_placeholder() → "需要 XXX_TOKEN"
    │
    └── 其他 25 个
        └── tools.execute(db, name, arg)
            ├── read_file, write_file, edit_file, list_directory
            ├── run_command (subprocess, 30s timeout)
            ├── search_memory, list_sessions, get_session
            ├── device_status (读心跳文件)
            └── 30+ device tools → device_tool_execute()
                └── 注入 debug_commands 队列
```

### 设备工具下发链路

```
tools.device_tool_execute(tool_name, code)
    │
    ├── 检查 collect_enabled 开关
    ├── 读 heartbeat_logs/mb-{code}.json
    ├── 写入 debug_commands[code] = {cmd, args, id, ts}
    └── 保存到 /var/lib/mbclaw/pending_commands.json
        │
        ▼ (客户端轮询)
    GET /admin/client/debug/cmd?code=xxx
        │
        ▼ (客户端上报结果)
    POST /admin/client/debug/result
```

---

## 五、Provider 调用流程

### 当前 4 条 LLM 调用路径

```
路径 1: MotherRuntime._build_candidates()
    └── app.token_pool.get_pool().keys (直接读文件)
    └── 状态: ✅ 主力使用

路径 2: LLMClient.__init__() fallback
    └── app.token_pool.get_pool().get_best_for_llm()
    └── 状态: ☑️ fallback (环境变量未配置时)

路径 3: LLMRouter._call_via_tokenpool()
    └── app.token_pool.get_pool()
    └── 状态: ❌ 被 MBOSCore 调用，基本不执行

路径 4: agent_run() (agent.py)
    └── httpx 直接调用 LLMClient 的 base_url
    └── 状态: ❌ 废弃
```

### 关键发现

**Mother 从未通过 HTTP 调用 TokenPool 服务（端口 8100）。**
Mother 内置的 `app/token_pool.py` 直接读取 `heartbeat_logs/` 文件来获取 Key，
完全绕过了 TokenPool 服务的 Scheduler、GuardRail、故障转移等核心功能。

---

## 六、数据库存储流程

```
init_db() (启动时)
    │
    ├── Base.metadata.create_all() — 建 7 张表
    ├── 执行 schema/fts.sql — 建 2 个 FTS5 虚拟表 + 6 个触发器
    └── PRAGMA: WAL + NORMAL sync + 20MB cache + MEMORY temp

运行时:
    ├── SessionLocal = sessionmaker (FastAPI Depends 注入)
    ├── 每请求: get_db() → yield db → close
    └── 高频写入: Message (每次对话)、工具调用
```

---

## 七、Pipeline 生命周期

```
Session 生命周期:
    POST /sessions          → create_session()
    POST /sessions/{sid}/messages → add_message()
    POST /sessions/{sid}/close    → close_session()
        │
        ├── 幂等: 已关闭返回缓存
        ├── LLM 摘要 + jieba 关键词
        ├── MemoryRepo 持久化
        └── session.status = "closed"
```

---

## 八、耦合分析

### 🔴 严重耦合

| 耦合点 | 问题 |
|--------|------|
| MotherRuntime ↔ app.token_pool | 直接读文件，绕过 TokenPool 服务 |
| tools.py ↔ debug_api_v2 | device_tool_execute 直接 import _debug_commands |
| main.py ↔ Gateway | 微信登录/WebChat 内联在 main.py |
| admin/ ↔ heartbeat_logs | 多处直接读 JSON 文件目录 |

### 🟡 中度耦合

| 耦合点 | 问题 |
|--------|------|
| mother_runtime.py ↔ agent.py | 两套 agent loop 并存 |
| LLMClient ↔ TokenPool | 循环 fallback 逻辑 |
| MotherRuntime ↔ MemoryRepo | System Prompt 硬编码工具列表 |

---

## 九、架构评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 功能完整性 | ⭐⭐⭐⭐ | Agent Loop + Memory + Tool + Gateway 完整 |
| 代码质量 | ⭐⭐⭐ | 意图清晰但有大量重复和废弃代码 |
| 模块边界 | ⭐⭐ | Mother/Panel 同进程，多处跨模块硬耦合 |
| 可测试性 | ⭐ | 无测试代码，强依赖文件系统和 TokenPool |
| 可扩展性 | ⭐⭐ | 工具系统 if-elif，Provider 路径分散 |
| 安全性 | ⭐⭐ | CORS *，部分管理 API 无鉴权 |

---

## 十、需要拆分的模块

| 模块 | 当前状态 | 建议 |
|------|---------|------|
| agent loop 实现 | 2 套 (mother_runtime + agent.py) | 合并为 1 套 |
| LLM Provider | 4 条路径 | 统一为 ProviderManager |
| 工具系统 | 3 套 (tools/skills/tool_runtime) | 统一 ToolRegistry |
| TokenPool 客户端 | 内置副本 + 独立服务 | Mother 通过 HTTP API 调 TokenPool |
| 管理面板数据 | admin JSON + Mother SQLite | 统一到 SQLite |
| Gateway 端点 | 内联在 main.py | 独立 GatewayRouter |
| System Prompt | 硬编码 3 处 | 统一配置 |
