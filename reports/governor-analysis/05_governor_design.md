# 任务五：MBclaw Governor 职责设计

> 仅输出职责，不写实现

## Governor 核心定位

Governor = 母体的"安全大脑"，在 Runtime 和 Capability 之间做决策。

```
                   ┌──────────────┐
                   │   Runtime    │
                   │  (执行流程)   │
                   └──────┬───────┘
                          │ 每个操作前咨询
                          ▼
                   ┌──────────────┐
                   │   Governor   │
                   │  (决策中心)   │
                   └──────┬───────┘
                          │ allow / deny / ask
                          ▼
                   ┌──────────────┐
                   │  Capability  │
                   │  (工具执行)   │
                   └──────────────┘
```

## Governor 流程

```
Runtime: 请求执行 action
    │
    ▼
[Policy Engine]
    检查: 操作是否在规则中？
    ├── blacklist 匹配 → DENY (立即拒绝)
    ├── whitelist 匹配 → ALLOW (立即放行)
    └── 不在任何列表 → 进入风险评估
    │
    ▼
[Risk Assessment]
    评分: 操作风险等级 (0-100)
    ├── risk < 20 → LOW
    ├── risk < 50 → MEDIUM
    └── risk >= 50 → HIGH
    │
    ▼
[Permission Check]
    检查: 当前用户/渠道是否有权限？
    ├── admin 用户 → 全部允许 (除 blacklist)
    ├── device (APK 端) → LOW 操作允许
    ├── gateway (QQ/微信) → LOW + 用户确认
    └── api (HTTP) → 按 API key 权限
    │
    ▼
[Action Decision]
    综合 Policy + Risk + Permission → 决策
    ├── ALLOW: 直接执行
    ├── DENY: 拒绝 + 日志
    └── ASK: 暂停，等待用户确认
    │
    ▼
[Checkpoint]  (仅 ALLOW + risk >= 30)
    保存当前状态快照
    │
    ▼
[Execution]  → Capability 执行
    │
    ├── 成功 → [Audit] 记录成功日志
    │
    └── 失败 → [Rollback]
        恢复 Checkpoint 快照
        记录失败日志
        返回错误 + 已回退提示
```

## 各组件职责

| 组件 | 职责 | 输入 | 输出 |
|------|------|------|------|
| Policy Engine | 规则匹配 | Action | blacklist/whitelist/unknown |
| Risk Assessment | 风险评分 | Action + Context | risk_score (0-100) |
| Permission Check | 权限判断 | User + Channel + Action | authorized: bool |
| Action Decision | 综合决策 | Policy + Risk + Permission | ALLOW/DENY/ASK |
| Checkpoint | 状态快照 | Session state | checkpoint_id |
| Rollback | 状态恢复 | checkpoint_id | restored state |
| Audit | 审计日志 | Decision + Result | 写入日志 |
