# 任务八：Evolution 迁移计划

> Evolution 是最高层能力，依赖所有底层模块 (Runtime / Memory / Governor / Scheduler) 成熟后才有意义。

---

## Phase 1 — Result Collection（0.5 天）

### 目标
收集每轮 Agent 执行结果，建立数据基础

### 前置依赖
- Runtime Phase 1+ (统一 Agent Loop)

### 新增
```
evolution/__init__.py
evolution/collector.py            ← ResultCollector
evolution/store.py                ← EvolutionStore (evolution_log 表)
```

### 数据库
```
CREATE TABLE evolution_log (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    trace_id TEXT,
    status TEXT,                  -- success / failure / corrected
    error_type TEXT,              -- 429 / timeout / 5xx / user_correction
    error_msg TEXT,
    turns INTEGER,                -- 使用轮数
    tools_used TEXT,              -- JSON: [tool_name, ...]
    latency_ms INTEGER,
    tokens_in INTEGER,
    tokens_out INTEGER,
    created_at TIMESTAMP
)
```

### Phase 1 完成标准
- 每 Session 结束时自动记录
- evolution_log 有数据积累
- 不做任何分析 (只收集)

---

## Phase 2 — Pattern Analysis（1 天）

### 目标
从数据中识别失败模式

### 前置依赖
- Phase 1 (有数据)
- Memory (Experience 表)

### 新增
```
evolution/analyzer.py             ← PatternAnalyzer
evolution/evaluator.py            ← ImpactEvaluator
```

### 修改
```
evolution/collector.py: 每次收集后调 analyzer.check_patterns()
```

### Phase 2 完成标准
- 自动识别重复模式 (≥3 次同类失败)
- 输出 PatternReport
- 写入 Memory (experience 的 kind=lesson)

---

## Phase 3 — Proposal Generation（1 天）

### 目标
针对模式自动生成改进方案

### 前置依赖
- Phase 2 (有模式)
- Governor (审批机制)
- Scheduler / TokenPool (可调参数)

### 新增
```
evolution/optimizer.py            ← Optimizer
evolution/proposal.py             ← OptimizationProposal
evolution/learner.py              ← ExperienceLearner
```

### Phase 3 完成标准
- 自动生成 OptimizationProposal
- 提交 Governor 审批
- cooldown / timeout / priority 参数可自动调整 (auto-approve)

---

## Phase 4 — Monitor + Rollback（1 天）

### 目标
改进效果监控 + 自动回滚

### 新增
```
evolution/monitor.py              ← EvolutionMonitor
evolution/rollback.py             ← RollbackManager
```

### Phase 4 完成标准
- 改进后 7 天监控
- 回归检测 → 自动回滚
- 回滚写入 evolution_log

---

## Phase 5 — Prompt Optimization（1.5 天）

### 目标
根据用户纠正优化 Prompt 模板

### 前置依赖
- Context Engine (templates/)
- Governor 审批 (HARD: 不改核心 Prompt)

### 新增
```
evolution/optimizer.py: PromptOptimizer
```

### Phase 5 完成标准
- 检测用户频繁纠正 → 分析原因
- 生成 Prompt 模板修改建议
- 需人工确认 (NEED_HUMAN)

---

## Phase 6 — AB Testing（远期，2 天）

### 新增
```
evolution/experiment.py           ← ABExperiment
```

---

## 工作量汇总

| Phase | 内容 | 天数 | 前置依赖 |
|-------|------|------|---------|
| Phase 1 | Result Collection | 0.5 天 | Runtime P1+ |
| Phase 2 | Pattern Analysis | 1 天 | Phase 1 + Memory |
| Phase 3 | Proposal Generation | 1 天 | Phase 2 + Governor + Scheduler/TokenPool |
| Phase 4 | Monitor + Rollback | 1 天 | Phase 3 |
| Phase 5 | Prompt Optimization | 1.5 天 | Phase 3 + Context Engine |
| Phase 6 | AB Testing | 2 天 (远期) | Phase 4 |
| **总计** | | **5 天 (不含 AB)** | |

## 优先级

Evolution 是 **P3 优先级**（远期）。

原因:
- 依赖所有底层模块 (至少 Runtime/Governor/Scheduler/Memory/TokenPool 全部 P1 完成)
- 当前影响最小 (无 Evolution 也能正常运行)
- 复杂度和风险最高 (自动修改系统参数)

---

## Evolution 铁律（实现时必须遵守）

```
1. Evolution 只提议，Governor 决定是否接受
2. 任何修改必须可回滚 (记录 before_value)
3. 修改核心代码 → HARD_DENY (Evolution 不能改自身)
4. 所有变更写入 evolution_log (审计)
5. 改进后必须监控 (7 天观察期)
6. 回归自动回滚 (阈值: 改善 < 预期 * 0.5)
```

---

## 当前可做的最小改进（不需要 Evolution Engine）

```
在 Session Close 时:
  1. 检查本 session 是否 ≥3 次相同错误
  2. 如果是 → 写入 experience (kind=failure)
  3. 下次 render_injection_for_new_session() 会提醒用户

这就是 Memory 已有的能力 → 不是 Evolution, 但有效。
```
