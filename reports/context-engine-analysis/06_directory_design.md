# 任务六：Context Engine 目录设计

```
context/
├── __init__.py          导出 ContextEngine
├── engine.py            主 ContextEngine 类
│   class ContextEngine:
│       build(messages, session, goal=None) → [messages]
│       compress(messages) → [messages]
│       restore(checkpoint_id) → [messages]
│       职责: 统筹所有子模块，输出最终 Prompt
│       替代: agent.py _build_context() + mother_runtime.py WorkingMemory
│
├── pipeline.py          Prompt 管道
│   class PromptPipeline:
│       layers: list[Layer]
│       add_layer(name, source, budget_pct)
│       assemble() → [messages]
│       职责: 按层序构建 Prompt
│       来源: 参考 Claude Code 分层 Prompt
│       替代: 当前硬编码 AGENT_PROMPT / SYSTEM_PROMPT 字符串
│
├── layers.py            Layer 定义
│   class Layer:
│       name: str              "system" / "governor" / "memory" / ...
│       source: callable       lambda: Memory.query(msg)
│       budget_pct: float      0.05 ~ 0.40
│       content: str           填充后的内容
│       职责: 定义每一层的来源和 Token 配额
│       来源: 新设计
│
├── compressor.py        压缩器
│   class Compressor:
│       compress(messages, budget) → compressed_messages
│       should_compress(messages, threshold) → bool
│       策略:
│         1. 重要性评分 (P0-P5)
│         2. 保留 P0-P3, 丢弃 P4-P5
│         3. LLM summarise_session() 生成语义摘要
│         4. 返回: [摘要, ...保留的消息]
│       职责: 智能压缩对话历史
│       来源: 参考 Claude Code Importance Compression + OpenHands Condenser
│       替代: WorkingMemory._maybe_compress() 的简单拼接
│
├── scorer.py            重要性评分
│   class ImportanceScorer:
│       score(message) → 0-10
│       规则:
│         P0: 用户明确指令 → 10
│         P1: 关键决策 → 8
│         P2: 工具执行结果 → 6
│         P3: 错误信息 → 5
│         P4: 已解决错误 → 2
│         P5: 低信息量 → 0
│       职责: 为每条消息评分
│       来源: 参考 Claude Code 保留策略
│       新功能 (当前无)
│
├── budget.py            Token 预算
│   class TokenBudget:
│       total: int              6000 (可配置)
│       allocations: dict[str, int]  {layer_name: tokens}
│       allocate() → 按比例分配
│       consume(layer_name, tokens) → 减少剩余
│       remaining() → int
│       职责: Token 配额管理
│       新功能 (当前无，只有粗略 total_tokens())
│
├── estimator.py         Token 估算
│   class TokenEstimator:
│       estimate(text) → int
│       策略: tiktoken (精确) / 字符数/4 (粗略)
│       count_messages(messages) → int
│       职责: 精确计算 Token 数
│       来源: 替代 WorkingMemory.total_tokens() 的 len//4
│
├── templates/           Prompt 模板 (YAML)
│   ├── identity.yml          Layer 1: 角色定义
│   ├── governor.yml          Layer 2: 权限约束 (动态注入)
│   ├── memory.yml            Layer 3: 记忆召回格式
│   ├── planner.yml           Layer 4: 任务状态格式
│   └── capability.yml        Layer 5: 工具列表格式
│       职责: 声明式 Prompt 模板 (非硬编码 Python 字符串)
│       替代: AGENT_PROMPT + SYSTEM_PROMPT + TOOL_DEFS_TEXT
│
├── checkpoint.py        Context 快照
│   class ContextCheckpoint:
│       save(messages, budget_state, compressor_state) → checkpoint_id
│       restore(checkpoint_id) → (messages, budget_state, compressor_state)
│       职责: 保存/恢复 Context Engine 完整状态
│       来源: 参考 Claude Code Checkpoint
│       新功能 (当前无)
│
└── preloader.py         Context 预热
    class ContextPreloader:
        preload(session_id) → preloaded_context
        职责: 会话创建时预加载 Memory + History (避免首次调用延迟)
        新功能 (当前无)
```

## 各文件职责精简

| 文件 | 职责 | 来源 | 替代 |
|------|------|------|------|
| engine.py | 统筹构建 Prompt | 新设计 | _build_context + WorkingMemory |
| pipeline.py | 分层组装 | Claude Code 分层 Prompt | AGENT_PROMPT/SYSTEM_PROMPT 字符串 |
| layers.py | Layer 定义 | 新设计 | 无 |
| compressor.py | 智能压缩 | Claude Code + OpenHands | _maybe_compress() |
| scorer.py | 重要性评分 | Claude Code 保留策略 | 无 |
| budget.py | Token 配额 | 新设计 | 无 (仅有粗略估算) |
| estimator.py | Token 计数 | 新设计 | total_tokens() len//4 |
| templates/ | Prompt 模板 | 新设计 | 硬编码 Python 字符串 |
| checkpoint.py | Context 快照 | Claude Code Checkpoint | 无 |
| preloader.py | 预热 | 新设计 | 无 |
