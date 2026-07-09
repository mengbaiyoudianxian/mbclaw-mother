# 任务一：MBclaw 当前 Runtime 完整生命周期

> 只读分析 | 精确到每一步调用、输入、输出、阻塞点、耦合点

---

## 发现：当前存在 **两套并行的 Runtime**

| Runtime | 文件 | 入口 | 用户 | 状态 |
|---------|------|------|------|------|
| **agent_run** | agent.py | POST /api/agent/run | HTTP API/控制面板 | 生产 |
| **MotherRuntime** | mother_runtime.py | Gateway (QQ/微信/Web) | 终端用户 | 生产 |

两者互不知道对方存在。代码重复率 ~60%。

---

## 流程图：agent_run (HTTP API 路径)

```
HTTP Client (Panel/curl)
    │
    ▼
api.py POST /agent/run              ← FastAPI, Depends(get_db), Depends(get_llm)
    │ 输入: AgentRequest{message, max_turns=5}
    │ 输出: JSON {session_id, response, tools_used, turns, thinking}
    │
    ▼
agent_run(db, session_id, message, llm, max_turns=5)
    │
    ├─[1] 读 Session ── db.query(SessionModel)
    │   ⚠️ 阻塞: 数据库 IO
    │   输出: session | ValueError(closed)
    │
    ├─[2] 写 User Message ── db.add(Message) + db.commit()
    │   ⚠️ 阻塞: 数据库写
    │
    ├─[3] 构建 System Prompt ── AGENT_PROMPT.format(tools_list=tools_text)
    │   来源: list_tools(db) → 数据库读取 tools 表
    │   🔗 耦合: 直接依赖 app.tools (硬编码 Tools 表)
    │
    ├─[4] Agent Loop (while turns < max_turns)
    │   │
    │   ├─[4a] 构建上下文 ── _build_context(db, session_id, current)
    │   │   输入: current=user_msg 或 tool_result
    │   │   内部: MemoryRepo.query() → FTS5 搜索
    │   │   内部: db.query(Message) → 最近 10 条消息
    │   │   ⚠️ 阻塞: 2 次数据库查询
    │   │   输出: ctx (string)
    │   │   🔗 耦合: 直接依赖 app.memory.MemoryRepo
    │   │
    │   ├─[4b] LLM 调用 ── httpx.post(f"{llm.base_url}/chat/completions")
    │   │   ⚠️ 阻塞: 网络 IO (timeout=120s!)
    │   │   输入: model + messages[system_prompt, user_ctx_msg]
    │   │   输出: raw (string) | 异常 → final="LLM调用失败"
    │   │   🔗 耦合: 直接 httpx, 不通过 LLMClient
    │   │   ❌ 无重试 | ❌ 无 fallback | ❌ 无 streaming
    │   │
    │   ├─[4c] 解析 ── TOOL_RE.finditer(raw) + THINK_RE.finditer(raw)
    │   │   输入: raw (LLM 输出)
    │   │   输出: [(tool_name, tool_content)], think_matches
    │   │   clean = 去掉 <tool>/<thinking> 的纯文本
    │   │
    │   ├─[4d] 执行工具 (if tool_matches)
    │   │   for tname, tcontent in tool_matches:
    │   │       exec_tool(db, tname, tcontent)  ← tools.py execute()
    │   │       ⚠️ 阻塞: 130 行 if/elif 链
    │   │       ⚠️ 阻塞: 子进程 (subprocess.run)
    │   │   🔗 耦合: 直接依赖 app.tools.execute
    │   │
    │   ├─[4e] 写 Tool Result Message ── db.add(Message) + db.commit()
    │   │
    │   └─[4f] 无 tool → break (最终回复)
    │
    ├─[5] 写 Final Message ── db.add(Message) + db.commit()
    │
    ▼
返回 {session_id, response, tools_used, turns, thinking}
```

## 流程图：MotherRuntime (Gateway 路径)

```
QQ/微信/Web 用户
    │
    ▼
Gateway Adapter (WechatAdapter / POST /gateway/web/chat)
    │
    ▼
gateway_agent.py handle_gateway_agent(msg, code)
    │ 生成 sid = hash(f"gateway:{code}") % 100000
    │ 输入: msg (string), code (device/user identifier)
    │
    ▼
get_runtime() → MotherRuntime (单例)
    │
    ▼
MotherRuntime.run(message, session_id, max_turns=5)
    │
    ├─[1] 获取/创建 Session ── _get_session(sid)
    │   WorkingMemory: in-memory, 6000 token limit
    │   输出: WorkingMemory 实例
    │   💡 不依赖数据库 (与 agent_run 不同)
    │
    ├─[2] 添加用户消息 ── wm.add("user", message)
    │   内部: _maybe_compress() → 80% 阈值触发压缩
    │
    ├─[3] 填充记忆召回 ── MemoryRepo(db_factory).query(message, 3)
    │   ⚠️ 阻塞: 数据库 IO (仅当 db_factory 可用)
    │   💡 优雅降级: db_factory=None 时跳过
    │   输出: wm.set_recall([摘要...])
    │
    ├─[4] Agent Loop (for turn in range(max_turns))
    │   │
    │   ├─[4a] 构建候选 ── _build_candidates()
    │   │   内部: token_pool.get_pool() → 遍历 keys
    │   │   优先级: custom > zhipu > deepseek-cn > miclaw-bridge > others
    │   │   ⚠️ 阻塞: 模块导入 + key 排序
    │   │   输出: [(base_url, api_key, model), ...]
    │   │   🔗 耦合: 直接依赖 app.token_pool
    │   │   ✅ 有 fallback: 最多试前 4 个
    │   │
    │   ├─[4b] LLM 调用 ── httpx.post(base_url/chat/completions)
    │   │   ⚠️ 阻塞: 网络 IO (timeout=15s)
    │   │   输入: model (候选中的模型), messages (wm.to_messages())
    │   │   输出: raw (string) | None (全部失败)
    │   │   ✅ 有重试: 遍历 candidates[:4]
    │   │   ❌ 无 streaming
    │   │   🔗 耦合: 直接 httpx, 不通过 LLMClient
    │   │
    │   ├─[4c] 解析 ── TOOL_RE.finditer(raw)
    │   │   输入: raw (LLM 输出)
    │   │   输出: [(tool_name, tool_content)]
    │   │
    │   ├─[4d] 执行工具 (if tool matches)
    │   │   最多 2 轮工具调用 (if turn >= 2: break)
    │   │   最多 3 个工具 (tcontent[:3])
    │   │   执行: _execute_tool(name, arg)
    │   │       ├─ github_* / ssh_exec → skills.py execute_skill()
    │   │       ├─ *_api (placeholder) → skills.py api_placeholder()
    │   │       └─ 其他 → tools.py execute(db, name, arg)
    │   │   ⚠️ 阻塞: 子进程 + 数据库 IO
    │   │   🔗 耦合: 同时依赖 skills.py 和 tools.py
    │   │
    │   └─[4e] 无 tool → break
    │
    ├─[5] 记录最终回复 ── wm.add("assistant", final_reply)
    │
    ▼
返回 {reply, turns, tool_calls}
    │
    ▼
gateway_agent.py: 去 Markdown (QQ 纯文本适配)
    │
    ▼
返回给用户
```

---

## 阻塞点汇总

| 阻塞点 | 位置 | 耗时 | 影响 |
|--------|------|------|------|
| 数据库读 (Session) | agent_run L1 | ~5ms | 中等 |
| 数据库写 (Message) | agent_run L2 | ~10ms | 中等 |
| 数据库读 (Memory FTS5) | agent_run L4a | ~20ms | 中等 |
| LLM 网络调用 | agent_run L4b | 2~30s | **核心瓶颈** |
| 子进程执行 | agent_run L4d | 1~8s | 按需 |
| 数据库写 (Tool Result) | agent_run L4e | ~10ms | 中等 |

## 耦合点汇总

| 耦合 | 文件 | 依赖 | 严重度 |
|------|------|------|--------|
| 直接 httpx | agent.py L143 | 无抽象层 | ⚠️ 高 |
| 直接 httpx | mother_runtime.py L172 | 无抽象层 | ⚠️ 高 |
| 硬编码 System Prompt | agent.py L14 | 字符串常量 | ⚠️ 高 |
| 硬编码 System Prompt | mother_runtime.py L110 | 字符串常量 | ⚠️ 高 |
| 直接依赖 tools | agent.py L154 | tools.execute | ⚠️ 高 |
| 直接依赖 tools+skills | mother_runtime.py L236 | 两个模块 | ⚠️ 高 |
| 直接依赖 token_pool | mother_runtime.py L200 | app.token_pool | 🔶 中 |
| 直接依赖 MemoryRepo | agent.py L74 | app.memory | 🔶 中 |
| 无 LLMClient 抽象 | 两处 | providers.py 被绕过 | ⚠️ 高 |
| 两套 prompt 不统一 | agent.py + mother_runtime.py | 维护成本翻倍 | ⚠️ 高 |

## 关键问题

1. **两套 Runtime 分裂**: agent_run 和 MotherRuntime 完全独立，但做同样的事
2. **LLM 调用绕过 LLMClient**: 直接 httpx，不经过 providers.py
3. **无恢复机制**: LLM 失败 → 字符串错误返回，用户只能重来
4. **无 streaming**: 全部阻塞等待完整响应
5. **无 checkpoint**: WorkingMemory 在内存中，进程重启丢失
6. **工具执行耦合**: 硬编码的路由 (github_/ssh_exec → skills, 其他 → tools)
