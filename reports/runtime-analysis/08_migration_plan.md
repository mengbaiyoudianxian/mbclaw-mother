# 任务八：迁移计划

---

## Phase 1 — 统一 Runtime（3 天，无外部依赖）

### 删除
```
无删除。合并 agent.py + mother_runtime.py -> runtime/runtime.py
agent.py agent_run()       -> 不再直接调用
mother_runtime.py run()    -> 不再直接调用
```

### 新增
```
runtime/__init__.py
runtime/runtime.py          <- MotherRuntime v2 (合并两个 run 方法)
runtime/loop.py             <- 提取 while/for 循环为 AgentLoop
runtime/worker.py           <- 提取 _execute_tool 为 Worker
runtime/observation.py      <- Observation dataclass
runtime/session.py          <- 提取 _get_session 为 SessionStore
```

### 修改
```
api.py POST /agent/run      -> 调用 runtime.MotherRuntime.run() 而非 agent_run()
gateway_agent.py            -> 调用 runtime.MotherRuntime 而非 mother_runtime
agent.py                    -> 保留，标记 deprecated
mother_runtime.py           -> 保留，标记 deprecated
```

### Phase 1 完成标准
- 两套 Runtime 统一为一个 MotherRuntime
- API 和 Gateway 都通过同一个入口
- Session 管理统一 (SessionStore)

---

## Phase 2 — 接入 Capability Registry（2 天）

### 删除
```
mother_runtime.py TOOL_DEFS_TEXT (硬编码工具列表)
agent.py AGENT_PROMPT 中的 tools_list 硬编码
```

### 修改
```
worker.py: 不直接 import tools + skills -> 通过 CapabilityRegistry 查找
runtime.py: System Prompt 中的工具列表从 Registry 动态生成
```

### 依赖
```
capabilities/registry.py (Capability Task 产出)
```

### Phase 2 完成标准
- 所有工具通过 CapabilityRegistry 执行
- System Prompt 从 Registry 动态生成

---

## Phase 3 — 接入 Context Engine（2 天，预留）

### 修改
```
runtime/loop.py: Context 构建 -> ContextEngine.build_prompt()
WorkingMemory: 迁移到 context/ 模块
```

### 依赖
```
context/ (Context Engine - 后续 Task)
```

---

## Phase 4 — 接入 Governor（1 天，预留）

### 修改
```
runtime/runtime.py: 生命周期管理 -> Governor
```

### 依赖
```
governor/ (Governor - 后续 Task)
```

---

## Phase 5 — 接入 Scheduler（2 天，预留）

### 修改
```
runtime/loop.py: LLM 调用 -> Scheduler
runtime/recovery.py: 故障转移 -> Scheduler fallback
```

### 依赖
```
scheduler/ (Scheduler - 后续 Task)
token_pool (TokenPool)
```

---

## 工作量汇总

| Phase | 内容 | 天数 | 依赖 | 状态 |
|-------|------|------|------|------|
| Phase 1 | 统一 Runtime | 3 天 | 无 | 立即可执行 |
| Phase 2 | Capability 接入 | 2 天 | Capability Task | 等待 Capability |
| Phase 3 | Context Engine 接入 | 2 天 | Context Task | 预留 |
| Phase 4 | Governor 接入 | 1 天 | Governor Task | 预留 |
| Phase 5 | Scheduler 接入 | 2 天 | Scheduler Task | 预留 |
| **当前可执行** | **Phase 1** | **3 天** | — | — |
| **总计 (含预留)** | Phase 1-5 | **10 天** | — | — |

## 影响范围

| 文件 | Phase 1 | Phase 2 | Phase 3-5 |
|------|---------|---------|-----------|
| agent.py | deprecated | 删除 | — |
| mother_runtime.py | deprecated | 删除 | — |
| gateway_agent.py | 改调用 | — | — |
| api.py | 改调用 | — | — |
| runtime/ | 新建 6 文件 | 修改 worker | 修改 loop/runtime |
