# 任务七：精确可参考源码

## OpenHands

| 文件 | 类/函数 | 参考什么 | 原因 |
|------|---------|---------|------|
| `openhands/app_server/app_conversation/app_conversation_service.py` | `AppConversationService` | Session 生命周期管理 (create/close/list) | 抽象接口设计 |
| `openhands/app_server/app_conversation/app_conversation_start_task_service.py` | `AppConversationStartTaskService` | Task 生命周期 (search/count/get/save/delete) | 抽象接口设计 |
| `openhands/app_server/services/injector.py` | `Injector` | 依赖注入模式 | Governor 初始化参考 |

## OpenClaw

| 文件 | 类/函数 | 参考什么 | 原因 |
|------|---------|---------|------|
| `src/agents/subagent-recovery-state.ts` | SubagentRecoveryState | 恢复状态: idle->running->recovering->done | 状态机参考 |
| `src/agents/tool-result-error.ts` | ToolResultError | 工具错误的类型化处理 | Observation.error 字段 |
| `src/agents/agent-steering-queue.ts` | AgentSteeringQueue | 消息队列: enqueue->dequeue->process | Worker 队列参考 |
| `src/agents/transcript-policy.ts` | TranscriptPolicy | 对话记录策略 | Session 记录 |
| `src/agents/usage.ts` | Usage tracking | 使用统计 | metrics |

## Claude Code（文档/公开仓库）

| 来源 | 设计 | 参考什么 | 原因 |
|------|------|---------|------|
| docs/ | Agent Loop | thinking <-> tool_use 交替 | 但仅 Claude 模型支持 |
| docs/ | Context Compression | 重要性评分保留 | 比时间截断更智能 |
| docs/ | Checkpoint | 状态快照 + 回退 | 错误恢复 |
| docs/ | Plugin Marketplace | marketplace.json 注册格式 | Capability 注册参考 |
| `claude-code-notes/plugins/README.md` | Plugin 开发指南 | 插件 hooks + commands | Capability 扩展机制 |

## Codex CLI (Rust)

| 文件 | 参考什么 | 原因 |
|------|---------|------|
| `codex-rs/core/src/state/session.rs` | Session 状态管理 | 显式状态机 |
| `codex-rs/execpolicy-legacy/` | 执行策略 (allow/deny/ask) | Compute 安全策略 |
| `codex-rs/cli/` | CLI 交互循环 | streaming + tool 解析 |
| `codex-rs/skills/` | 技能系统 build.rs 注入 | 编译时注册机制 |

## 不参考的

| 项目 | 文件 | 原因 |
|------|------|------|
| OpenHands | `openhands/server/sandbox/` | Docker Sandbox — 不需要 |
| OpenHands | `openhands/app_server/integrations/` | GitHub/GitLab 集成 — 不属于 Runtime |
| Codex CLI | `codex-rs/bwrap/` | Bubblewrap 沙箱 — 不需要 |
| Codex CLI | `codex-rs/windows-sandbox-rs/` | Windows 沙箱 — 不需要 |
