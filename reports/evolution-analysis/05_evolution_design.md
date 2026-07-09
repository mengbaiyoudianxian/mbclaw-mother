# 任务五：Evolution 最终设计

## 核心定位

```
Memory:    "保存经验"    — 过去发生了什么
Evolution: "改变未来行为" — 基于经验提出改进
Governor:  "批准改变"    — 是否接受改进建议
Planner:   "当前规划"    — 下一步做什么
Runtime:   "当前执行"    — 现在怎么执行
```

---

## Evolution 职责范围

### ✅ Evolution 负责

| 职责 | 说明 |
|------|------|
| **结果收集** | 收集每轮 Agent 执行结果 |
| **模式识别** | 从多次失败中识别模式 |
| **影响评估** | 评估改进建议的预期效果 |
| **经验提取** | 从成功/失败中提取可复用经验 |
| **改进建议生成** | 生成具体优化方案 |
| **建议提交审批** | 提案 → Governor 审核 |
| **效果监控** | 改进后监控效果 |
| **回滚触发** | 效果恶化 → 建议回滚 |

### ❌ Evolution 不负责

| 职责 | 归属 | 原因 |
|------|------|------|
| 保存经验 | Memory | Evolution 读取但不存储 |
| 当前 Prompt | Context Engine | Evolution 管长期 |
| 当前任务 | Planner | Evolution 提建议 |
| 当前执行 | Runtime | Evolution 不实时干预 |
| 直接修改系统 | Governor | Evolution 只提议 |

---

## Evolution 铁律

```
Evolution 可以:
  ✅ 分析失败模式
  ✅ 提出改进建议
  ✅ 建议调整 Runtime 参数
  ✅ 建议更新 Memory
  ✅ 建议修改 Capability 配置

Evolution 不能:
  ❌ 自我突破权限 (HARD_DENY)
  ❌ 绕过安全策略
  ❌ 直接修改核心代码
  ❌ 直接改变 Governor 规则
  ❌ 在无审批的情况下应用任何改变
```

## Evolution 与 Governor 的关系

```
Evolution 提交 Proposal:
  {
    type: "config_change" | "memory_update" | "skill_update" | "policy_suggest"
    target: "scheduler.cooldown_seconds" | "memory.experience" | ...
    current_value: 30
    proposed_value: 60
    reason: "连续3次429后30s冷却不足以恢复 → 建议60s"
    evidence: [{timestamp, error_type, error_msg}, ...]
  }

Governor 审核:
  ├── HARD_DENY → 修改自身核心代码 → REJECT
  ├── 修改 Runtime 参数 → ALLOW
  ├── 更新 Memory → ALLOW
  ├── 修改 Capability → ALLOW (需人工确认)
  └── 修改 Governor 规则 → REJECT (需人工)
```

## Evolution 作用域

| 可改进 | 方式 | Governor |
|--------|------|:---:|
| TokenPool cooldown 时长 | 分析 429 模式 → 建议调整 | ALLOW |
| Provider 优先级 | 分析成功率 → 建议重排 | ALLOW |
| Tool 参数默认值 | 分析超时 → 建议增加 timeout | ALLOW+人工 |
| Memory 召回数 top_n | 分析相关度 → 建议调整 | ALLOW |
| Prompt 模板 | 分析用户纠正 → 建议优化 | ALLOW+人工 |
| Capability 参数 | 分析错误 → 建议修复 | ALLOW+人工 |
| Scheduler 重试次数 | 分析 failover 模式 | ALLOW |
| Governor 规则 | — | REJECT |
| 核心代码 | — | REJECT |
