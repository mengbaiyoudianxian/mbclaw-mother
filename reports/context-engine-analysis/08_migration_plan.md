# 任务八：Context Engine 迁移计划

---

## Phase 1 — 统一 Prompt 构建（1 天）

### 目标
将 2 套 Prompt + 2 套 Context 统一为一个 ContextEngine

### 新增
```
context/__init__.py
context/engine.py                ← ContextEngine (最小实现)
context/pipeline.py              ← PromptPipeline
context/layers.py                ← Layer 定义
context/templates/
  ├── identity.yml               ← 角色定义 (替代 AGENT_PROMPT/SYSTEM_PROMPT)
  ├── governor.yml               ← 空 (预留)
  ├── memory.yml                 ← 记忆召回格式
  └── capability.yml             ← 工具列表格式
```

### 删除
```
agent.py AGENT_PROMPT (硬编码)    → 移入 templates/identity.yml
mother_runtime.py SYSTEM_PROMPT   → 移入 templates/identity.yml
mother_runtime.py TOOL_DEFS_TEXT   → 移入 templates/capability.yml
```

### 修改
```
agent.py _build_context():  → 调用 context.engine.build()
mother_runtime.py WorkingMemory.set_system(): → 从 templates 加载
```

### Phase 1 完成标准
- 所有 Prompt 从 YAML 模板加载 (非硬编码字符串)
- ContextEngine.build() 输出统一格式的 messages
- 行为与当前一致 (Phase 1 不改变输出)

---

## Phase 2 — Token Budget + 精确估算（1 天）

### 目标
Token 预算管理 + 精确 Token 计数

### 新增
```
context/budget.py                ← TokenBudget
context/estimator.py             ← TokenEstimator
```

### 修改
```
context/engine.py: build() 前分配 Budget
context/pipeline.py: 按 Budget 截断每层
mother_runtime.py WorkingMemory.total_tokens(): 替换为 estimator.estimate()
```

### Phase 2 完成标准
- 每层有显式 Token 配额
- 超出配额自动截断
- Token 估算从 len//4 → tiktoken

---

## Phase 3 — 智能压缩（1.5 天）

### 目标
重要性评分 + LLM 语义摘要替代简单拼接

### 新增
```
context/compressor.py            ← Compressor
context/scorer.py                ← ImportanceScorer
```

### 修改
```
context/engine.py: build() 前检查 overflow → compress()
mother_runtime.py WorkingMemory._maybe_compress(): 替换为 Compressor.compress()
```

### Phase 3 完成标准
- 重要性评分 (P0-P5) 决定保留/丢弃
- 压缩生成 LLM 语义摘要 (非简单拼接)
- 压缩后语义完整性不低于 80%

---

## Phase 4 — Checkpoint + 预热（1 天）

### 目标
Context 快照 + Session 预热

### 新增
```
context/checkpoint.py            ← ContextCheckpoint
context/preloader.py             ← ContextPreloader
```

### Phase 4 完成标准
- 关键操作前保存 Context 快照
- LLM 失败后恢复 Context (与 Governor rollback 协作)
- Session 创建时预加载 Memory + History

---

## Phase 5 — 全模块接入（1 天）

### 目标
Governor/Planner/Capability/Memory 全部接入 Context Engine

### 修改
```
context/pipeline.py: add_layer("governor", Governor.get_policy)
context/pipeline.py: add_layer("planner", Planner.get_status)
context/pipeline.py: add_layer("capability", CapabilityRegistry.list)
runtime/runtime.py: LLM 调用 → context.engine.build() → Scheduler
```

### Phase 5 完成标准
- 8 层 Prompt 全部动态注入 (非硬编码)
- 所有模块通过 Context Engine 提供 Prompt 数据
- 无模块绕过 Context Engine 直接拼 Prompt

---

## 工作量汇总

| Phase | 内容 | 天数 | 依赖 |
|-------|------|------|------|
| Phase 1 | 统一 Prompt 构建 | 1 天 | 无 |
| Phase 2 | Token Budget + 估算 | 1 天 | Phase 1 |
| Phase 3 | 智能压缩 | 1.5 天 | Phase 2 |
| Phase 4 | Checkpoint + 预热 | 1 天 | Phase 3 |
| Phase 5 | 全模块接入 | 1 天 | Phase 4 + Runtime + Governor + Planner + Capability |
| **总计** | | **5.5 天** | |

## 影响范围

| 文件 | Phase 1 | Phase 2-3 | Phase 4-5 |
|------|---------|-----------|-----------|
| agent.py AGENT_PROMPT | ❌ 删除 | — | — |
| mother_runtime.py SYSTEM_PROMPT | ❌ 删除 | — | — |
| mother_runtime.py TOOL_DEFS_TEXT | ❌ 删除 | — | — |
| mother_runtime.py WorkingMemory | ✏️ 改 | ❌ 删除 (被替代) | — |
| agent.py _build_context() | ✏️ 改调用 | ❌ 删除 | — |
| context/ | ✨ 新建 8 文件 | ✨ 新建 2 文件 | ✨ 新建 2 文件 |

## Context Engine vs Memory 边界（重点重申）

```
Memory:                        Context Engine:
  存储长期记忆                   不存储任何数据
  提供 query() 接口              决定取几条、放哪层、分配多少 Token
  管理 FTS5 索引                 管理 Token Budget
  提取 experiences               管理压缩策略

协作流程:
  Context Engine 说: "给我 3 条相关记忆，900 tokens"
  Memory 返回: [summary1, summary2, summary3]
  Context Engine 截断: 每个 summary 最多 300 tokens
  拼入 Layer 3

Context Engine 不取代 Memory，不存储记忆。
它只是 Memory 的"消费者"和"编排者"。
```

## 优先级

Context Engine 是 **P1 优先级**（与 Governor/Scheduler 同级）。

原因:
- 当前两套 Prompt 维护成本翻倍
- 压缩策略粗糙（简单拼接丢失语义）
- 无 Token Budget（可能超过模型上限）
- 但必须先有统一 Runtime (Phase 1) 才能接入
