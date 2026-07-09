# 任务六：Governor 目录设计

```
governor/
├── __init__.py          导出 Governor
├── governor.py          主 Governor 类
│   class Governor:
│       assess(action, context) → Decision
│       职责: 统筹所有子模块，返回最终决策
│       流程: policy → risk → permission → decision
│
├── policy.py            策略引擎
│   class PolicyEngine:
│       rules: list[PolicyRule]
│       check(action) → PolicyResult
│       职责: 规则匹配 (blacklist/whitelist/asklist)
│       来源: 借鉴 Codex CLI policy.rs
│       替代: tool_runtime._allow() + tools.py STABLE/HIGH/DEVICE
│
├── risk.py              风险评估
│   class RiskAssessor:
│       assess(action, context) → risk_score (0-100)
│       职责: 计算操作风险
│       维度: 破坏性、可逆性、影响范围、数据敏感度
│
├── permission.py        权限检查
│   class PermissionChecker:
│       check(user, channel, action) → authorized: bool
│       职责: 用户/渠道权限验证
│       来源: 替代 admin/router.py require_admin (admin 面板)
│              新增 gateway (QQ/微信) 用户权限
│
├── decision.py          决策引擎
│   class DecisionEngine:
│       decide(policy, risk, permission) → Decision(ALLOW|DENY|ASK)
│       职责: 综合三个维度做最终决策
│       来源: 新设计 (当前无)
│
├── checkpoint.py        状态快照
│   class CheckpointManager:
│       save(session_id, snapshot) → checkpoint_id
│       restore(checkpoint_id) → snapshot
│       list(session_id) → checkpoints
│       职责: 保存/恢复 Runtime 状态
│       来源: 借鉴 Claude Code Checkpoint
│       新功能 (当前无)
│
├── rollback.py          状态回退
│   class RollbackManager:
│       rollback(session_id, checkpoint_id, reason) → result
│       职责: 执行回退，清理中间状态
│       来源: 借鉴 Claude Code Rollback
│       新功能 (当前无)
│
├── approval.py          用户审批
│   class ApprovalManager:
│       request_approval(session_id, action, reason) → approved: bool
│       pending_approvals → list
│       职责: ASK 决策的审批流程
│       来源: 新设计 (当前无)
│       渠道: QQ/微信询问"是否允许？"，Web/API 返回 confirm 提示
│
└── audit.py             审计日志
    class AuditLogger:
        log_decision(action, decision, user, channel, reason)
        log_execution(action, result, duration)
        query(filters) → logs
        职责: 所有 Governor 决策和执行结果的审计
        来源: 新设计 (当前无)
```

## 各文件职责精简

| 文件 | 职责 | 来源 | 状态 |
|------|------|------|------|
| governor.py | 统筹所有子模块 | 新设计 | 新建 |
| policy.py | 规则匹配 (黑/白/询问列表) | Codex CLI policy.rs | 新建 |
| risk.py | 风险评分 (0-100) | 新设计 | 新建 |
| permission.py | 用户/渠道权限 | admin/router.py 升级 | 迁移+增强 |
| decision.py | 综合决策 (ALLOW/DENY/ASK) | 新设计 | 新建 |
| checkpoint.py | 状态快照 | Claude Code Checkpoint | 新建 |
| rollback.py | 状态回退 | Claude Code Rollback | 新建 |
| approval.py | 用户审批 | 新设计 | 新建 |
| audit.py | 审计日志 | 新设计 | 新建 |
