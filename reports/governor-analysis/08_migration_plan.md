# 任务八：Governor 迁移计划

---

## Phase 1 — 抽离权限判断（1 天）

### 目标
将散落在各文件的权限逻辑集中到 `governor/policy.py`

### 删除
```
tools.py STABLE_TOOL_NAMES       → 移入 policy.py whitelist
tools.py HIGH_IMPACT_TOOL_NAMES  → 移入 policy.py asklist
tools.py DEVICE_TOOL_NAMES       → 移入 policy.py device_rules
tools.py _tool_status()          → 删除 (被 policy.check() 替代)
tool_runtime.py blocked 列表      → 移入 policy.py HARD_DENY
```

### 新增
```
governor/__init__.py
governor/governor.py             ← Governor 主类 (空壳，Phase 1 只搭框架)
governor/policy.py               ← PolicyEngine + HARD_DENY + whitelist + asklist
```

### 修改
```
tools.py execute(): 执行前调 Governor.assess() (Phase 1 默认 allow，不改变行为)
mother_runtime.py _execute_tool(): 同上
```

### Phase 1 完成标准
- PolicyEngine 包含所有现有规则
- 行为与当前完全一致 (默认 allow)
- 审计日志基础框架

---

## Phase 2 — Policy Engine（1 天）

### 目标
Policy Engine 正式接管所有操作决策

### 新增
```
governor/decision.py             ← DecisionEngine: ALLOW/DENY/ASK
governor/audit.py                ← AuditLogger
```

### 修改
```
governor/policy.py: check() 返回 PolicyResult (不只是 bool)
governor/governor.py: assess() 调用 policy → decision
```

### Phase 2 完成标准
- 所有工具执行前经过 Governor.assess()
- DENY 操作被拦截 + 审计日志记录
- WHITELIST/ASKLIST 规则生效

---

## Phase 3 — Risk Engine（1 天）

### 目标
增加风险评分，ASK 操作用户确认

### 新增
```
governor/risk.py                 ← RiskAssessor
governor/permission.py           ← PermissionChecker
governor/approval.py             ← ApprovalManager
```

### 修改
```
governor/governor.py: assess() 流程: policy → risk → permission → decision
governor/decision.py: 综合 policy+risk+permission 做决策
```

### Phase 3 完成标准
- Risk 评分 0-100 影响决策
- Gateway 用户对 ASK 操作收到确认提示
- Admin 用户自动跳过 ASK

---

## Phase 4 — Checkpoint + Rollback（1 天）

### 目标
关键操作前保存状态，失败时回退

### 新增
```
governor/checkpoint.py           ← CheckpointManager
governor/rollback.py             ← RollbackManager
```

### 修改
```
governor/governor.py: ALLOW + risk>=30 → checkpoint.save() before execute
runtime/session.py: 暴露 snapshot() 方法给 CheckpointManager
```

### Phase 4 完成标准
- HIGH 操作前自动保存 Checkpoint
- 执行失败 → 自动 rollback
- 回退后用户收到"已回退"提示

---

## Phase 5 — Rollback 完善（0.5 天）

### 目标
完善回退策略（重试/跳过/终止）

### 修改
```
governor/rollback.py: 增加 retry_policy: retry | skip | abort
governor/governor.py: rollback 后按 policy 决定下一步
```

### Phase 5 完成标准
- 失败后可配置: 重试 1 次 / 跳过 / 终止
- 重试前等待 checkpoint 恢复完成

---

## Phase 6 — Runtime 接入（0.5 天）

### 目标
Runtime 全面接入 Governor

### 修改
```
runtime/runtime.py: 每个 action 前调 governor.assess()
runtime/worker.py: execute() 前调 governor.assess()
runtime/loop.py: LLM 调用前调 governor.assess() (配额检查)
```

### Phase 6 完成标准
- 无绕过 Governor 的操作路径
- 所有操作有审计日志

---

## 工作量汇总

| Phase | 内容 | 天数 | 依赖 |
|-------|------|------|------|
| Phase 1 | 抽离权限 | 1 天 | 无 |
| Phase 2 | Policy Engine | 1 天 | Phase 1 |
| Phase 3 | Risk + Permission + Approval | 1 天 | Phase 2 |
| Phase 4 | Checkpoint + Rollback | 1 天 | Phase 3 |
| Phase 5 | Rollback 策略 | 0.5 天 | Phase 4 |
| Phase 6 | Runtime 接入 | 0.5 天 | Runtime Phase 1 |
| **总计** | | **5 天** | |

## 影响范围

| 文件 | Phase 1 | Phase 2 | Phase 3-6 |
|------|---------|---------|-----------|
| tools.py STABLE/HIGH/DEVICE | ❌ 删除 | — | — |
| tools.py _tool_status() | ❌ 删除 | — | — |
| tool_runtime.py blocked | ❌ 删除 | — | — |
| governor/ | ✨ 新建 2 文件 | ✨ 新建 2 文件 | ✨ 新建 4 文件 |
| runtime/ | — | — | ✏️ 接入 Governor |
