# 任务四：Claude Code Checkpoint/Rollback 分析

## Claude Code Checkpoint 设计

```
每次工具执行前:
  save_checkpoint()
    ├── file_snapshot: {path: hash}   ← Git 级文件快照
    ├── context_snapshot: messages     ← 对话状态
    └── metadata: {turn, tool, time}

用户拒绝 / LLM 错误:
  rollback_to_checkpoint()
    ├── restore files  (git checkout)
    ├── restore context (重建 messages)
    └── 重试 or abort
```

## 应该放 Governor 的设计

| 设计 | 原因 |
|------|------|
| **Checkpoint 保存** | 需要 Governor 决策何时保存快照 (每个 tool call 前) |
| **Rollback 决策** | 需要 Governor 判断: 回退到哪个 checkpoint？ |
| **Rollback 策略** | 需要 Governor 控制: 重试 / skip / abort？ |
| **上下文保护** | 需要 Governor 过滤: 回退时保留哪些消息？ |
| **Long Task Resume** | 需要 Governor 管理: 长任务暂存 + 恢复 |

## 应该放 Runtime 的设计

| 设计 | 原因 |
|------|------|
| **Checkpoint 执行** | Runtime 负责实际保存/恢复 WorkingMemory |
| **文件回退** | Runtime 的 Worker 负责文件操作 |
| **对话重建** | Runtime 的 Session 负责消息重建 |

## Governor ↔ Runtime 协作流程

```
Runtime: "即将执行 run_command(rm -rf /tmp/test)"
    → Governor: checkpoint.save(session_id, wm.snapshot())
    → Governor: policy.check(run_command, params) → DENY
    → Governor: "危险操作，已拦截"
    → Runtime: 返回拒绝消息给用户

Runtime: "即将执行 write_file(/etc/config)"
    → Governor: policy.check(write_file, params) → ASK
    → Governor: "需要用户确认"
    → (用户确认)
    → Governor: checkpoint.save() → policy.ALLOW
    → Runtime: 执行 write_file
    → (执行失败)
    → Governor: rollback.restore(checkpoint)
    → Runtime: 返回错误 + 已回退
```

## 可直接借鉴

| Claude 设计 | Governor 组件 | 说明 |
|------------|-------------|------|
| save_checkpoint | checkpoint.py | 对话状态快照 (不包含文件) |
| rollback_to_checkpoint | rollback.py | 恢复对话状态 |
| context_snapshot | checkpoint.py | WorkingMemory.to_dict() |
| 用户拒绝回退 | rollback.py | AGENT_REJECT → rollback |

## 不能迁移

- Git 级文件快照: MBclaw 是对话场景，不需要文件回退
- /compact 命令: MBclaw 自动触发

## 推荐指数

★★★★☆ — Checkpoint + Rollback 是 Governor 核心能力
