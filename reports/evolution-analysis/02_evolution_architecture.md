# 任务二：Evolution 架构分析

## 当前架构：Evolution 不存在 → 零架构

```
┌─────────────────────────────────────────────┐
│                Memory (唯一间接关联)          │
│                                             │
│  experiences 表:                             │
│    kind: success / failure / lesson          │
│    title + content                           │
│                                             │
│  render_injection_for_new_session():          │
│    "避免重复的失败" + "已验证的成功"           │
│    → 注入 Context (不改变系统)                │
└─────────────────────────────────────────────┘
```

## 应该的架构（设计稿）

```
输入:
  ├── Memory (experiences)
  ├── Runtime Logs (每轮 Agent 执行结果)
  ├── Execution Result (成功/失败/错误类型)
  ├── User Feedback (👍/👎/纠正)
  └── Error Report (异常堆栈)

        │
        ▼
┌─────────────────────────────────────────────┐
│              Evolution Engine                │
│                                             │
│  Analyzer     → 失败模式识别                  │
│  Evaluator    → 影响评估                      │
│  Learner      → 从经验中学习                   │
│  Optimizer    → 生成改进建议                   │
│  Experiment   → AB 测试 (远期)                │
│  Rollback     → 回滚失败的改进                 │
└────────┬────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│              Governor (审批层)                │
│   所有改进建议 → Governor 审核 → accept/reject │
└────────┬────────────────────────────────────┘
         │ accept
         ▼
输出:
  ├── Knowledge Update (更新 Memory)
  ├── Skill Update (更新 Capability/Tools)
  ├── Policy Update (更新 Governor 规则)
  └── System Improvement (更新 Runtime 参数)
```

## Evolution 生命周期（设计稿）

```
Task Complete
    │
    ▼
Collect Result  ← ExecutionResult {success, error_type, latency, tool_used, ...}
    │
    ▼
Evaluate        ← 判断: 正常 / 警告 / 失败 / 需改进
    │
    ▼
Detect Pattern  ← 多次同类失败 → 识别模式
    │              "连续3次 429 → 需要添加cooldown"
    │              "用户频繁纠正输出 → Prompt需要优化"
    │
    ▼
Extract Experience → Memory.Write(experience)
    │
    ▼
Generate Improvement → OptimizationProposal
    │              "建议: 将 provider priority 从 custom 改为 zhipu"
    │              "建议: 为 tool X 增加 timeout 参数"
    │
    ▼
Governor Review  ← approve / reject / modify
    │              HARD_DENY: 不能修改自身核心代码
    │              ALLOW: 可以调整 Runtime 参数
    │              ALLOW: 可以更新 Memory
    │
    ▼
Apply           ← 执行改进
    │
    ▼
Monitor         ← 观察改进效果
    │
    ▼
Rollback        ← 如果恶化 → 回滚
```

---

## Evolution 不负责的铁律

| 不负责 | 归属 | 理由 |
|--------|------|------|
| 保存长期数据 | Memory | Evolution 读取 Memory，不存储 |
| 当前 Context | Context Engine | Evolution 不管当前 |
| 当前任务规划 | Planner | Evolution 提长期建议 |
| 当前执行 | Runtime | Evolution 不实时干预 |
| 直接修改系统 | Governor | Evolution 只提议 |
