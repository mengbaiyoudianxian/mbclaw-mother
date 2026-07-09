## ADR-006: Planner 显式决策

Status: Accepted (2026-07-09)

### 决策
Planner 在 LLM 调用前分析意图，决定是否需要工具。意图分类: chat | tool_request | ambiguous。

### 实现
优先规则匹配(关键词/模式)，未来可引入轻量分类模型。
