# 任务六：Runtime 目录设计

```
runtime/
├── __init__.py          导出 MotherRuntime
├── runtime.py           主 Runtime 类 (替代 agent_run + MotherRuntime)
│   MotherRuntime.run(message, session_id) -> Reply
│   职责: 编排完整流程 Receive->Context->Scheduler->Worker->Reply
│
├── loop.py              Agent Loop (独立)
│   class AgentLoop:
│       run(messages, tools, llm, max_turns) -> result
│       职责: while turns < max_turns: LLM->parse->execute->repeat
│       来源: 提取 agent_run 的 while + MotherRuntime 的 for
│
├── worker.py            工具执行器
│   class Worker:
│       execute(tool_name, params, policy) -> Observation
│       职责: 路由到 CapabilityRegistry -> 执行 -> 包装结果
│       来源: 提取 MotherRuntime._execute_tool()
│
├── session.py           会话管理
│   class SessionContext:
│       id, user_id, channel, context(WorkingMemory), state
│   class SessionStore:
│       get(sid), create(), close(sid), list_active()
│       职责: Session 生命周期管理
│       来源: 提取 MotherRuntime._get_session() + _sessions dict
│
├── state.py             状态机
│   class RuntimeState(Enum):
│       IDLE, RUNNING, WAITING_TOOL, WAITING_USER, DONE, ERROR
│   class StateMachine:
│       transition(from, to) -> bool
│       职责: 显式状态管理 (当前无)
│       来源: 参考 Codex CLI session.rs 状态机
│
├── stream.py            流式响应
│   class StreamHandler:
│       handle_sse(chunks) -> 增量解析 tool_calls
│       职责: 处理 SSE streaming 响应
│       来源: 参考 Claude Code streaming loop
│
├── checkpoint.py        恢复点
│   class Checkpoint:
│       save(session_id, state_snapshot)
│       restore(session_id) -> state_snapshot
│       职责: 保存/恢复 Runtime 状态 (LLM 失败时回退)
│       来源: 参考 Claude Code Checkpoint
│
├── recovery.py          故障恢复
│   class RecoveryPolicy:
│       on_llm_error(error) -> retry | fallback | degrade | abort
│       on_tool_error(error) -> retry | skip | abort
│       职责: 错误恢复策略
│       来源: 提取 MotherRuntime 的 candidates[:4] 重试逻辑
│
└── observation.py       观察模型
    class Observation:
        type: tool_result | error | timeout | user_input
        tool: str
        result: any
        error: str | None
        duration: float
        职责: 统一的工具执行结果模型 (替代裸字符串)
        来源: 参考 OpenHands Observation
```

## 各文件职责映射

| 文件 | 职责 | 来源/映射 |
|------|------|----------|
| runtime.py | 编排器 | 合并 agent_run + MotherRuntime |
| loop.py | 纯循环 | 提取 while/for 循环 |
| worker.py | 工具执行 | MotherRuntime._execute_tool() |
| session.py | 会话生命周期 | MotherRuntime._sessions |
| state.py | 显式状态机 | 新增 (参考 Codex CLI) |
| stream.py | SSE streaming | 新增 (参考 Claude Code) |
| checkpoint.py | 状态快照/恢复 | 新增 (参考 Claude Code) |
| recovery.py | 错误恢复策略 | MotherRuntime candidates[:4] |
| observation.py | 统一结果模型 | 新增 (参考 OpenHands) |
