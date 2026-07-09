# 任务四：Codex CLI Runtime 分析

## 核心发现

Codex CLI 已从 TypeScript 迁移到 Rust (codex-rs/)。开源但执行策略部分闭源。
Rust 代码不兼容 Python，仅作设计参考。

## Codex CLI Runtime 设计

```
CLI 入口 (Rust)
  → Session 初始化 (codex-rs/core/src/state/session.rs)
  → Prompt Pipeline:
     1. System Prompt
     2. Workspace Context
     3. Conversation History (压缩后)
     4. User Message
  → OpenAI API (streaming)
  → 流式解析 (边接收边处理 tool_calls)
  → 执行策略检查 (execpolicy):
     allow → 直接执行
     deny → 拒绝
     ask → 询问用户
  → Sandbox 执行 (bwrap)
  → 结果反馈 → 循环
```

## 可直接参考

| 设计 | MBclaw 应用 | 为什么 |
|------|------------|--------|
| Prompt Pipeline | Context Engine: 分层构建 prompt（基座+规则+工具+记忆+用户） | 清晰的分层架构 |
| 执行策略 (allow/deny/ask) | Compute: CommandPolicy 三级审批 | 安全性提升 |
| Streaming 解析 | Scheduler: 流式 LLM 响应 | 减少用户等待 |
| Session 状态机 | session.py: 显式状态管理 (idle/running/waiting_tool/done/error) | 当前无状态 |

## 可直接复制思路

| Codex 实现 | 翻译为 Python |
|-----------|-------------|
| execpolicy allow/deny/ask | CommandPolicy.check(cmd) -> allow|deny|ask |
| prompt_pipeline 4层构建 | ContextEngine.build_prompt(): system+rules+tools+memory+user |
| session.rs 状态管理 | Session.state: idle|running|waiting_tool|done |

## 不要的

- Rust 运行时 — Python 不兼容
- Bubblewrap 沙箱 — 移动设备不需要
- Windows 沙箱 — 不需要
- WASM 技能编译 — Python 不需要

## 推荐指数

★★★☆☆ — 执行策略 + Prompt Pipeline 设计值得参考，但 Rust 实现无法复用
