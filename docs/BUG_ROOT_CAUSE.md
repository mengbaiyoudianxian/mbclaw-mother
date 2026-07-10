# BUG_ROOT_CAUSE.md — "（母体已处理，无文字回复）"

**Date:** 2026-07-11
**Status:** ROOT CAUSE IDENTIFIED — NOT YET FIXED

---

## 1. Symptom

用户发送 "你好"，母体返回：

```
（母体已处理，无文字回复）
```

不是超时、不是500、不是崩溃。Kernel 正常执行完 pipeline，但最终 reply 对 Gateway 来说不包含有效回复内容。

---

## 2. Full Trace: "你好" Request

### 2.1 Request enters kernel

```
用户: "你好"
  ↓
Gateway → MBOSKernel.process("你好", session_id=1)
```

### 2.2 Pipeline execution

| Phase | Component | Action | Result |
|---|---|---|---|
| 0 | EventKernel | `RequestEvent` published | ✅ |
| 1 | Governor | Constitution check → `allow` | ✅ |
| — | Emergency | `is_stopped()` → `False` | ✅ |
| 2 | Planner | `create_plan("你好")` | 3 tasks: `task_1`(analysis), `task_2`(action), `task_3`(observe) |
| 3 | Scheduler | `schedule_graph()` | All 3 dispatched to workers llm-1, tool-1, sys-1 |
| 4 | Audit + Memory | Events persisted | 10 audit entries, memory stored |

### 2.3 Reply construction (kernel.py lines 365-381)

```python
# Build reply
scheduled_count = sum(1 for r in schedule_results if r.success)
failed_schedules = [r for r in schedule_results if not r.success]

if failed_schedules:
    reply = (
        f"任务规划完成: {task_graph.goal}\n"
        f"共 {len(task_graph.tasks)} 个任务, "
        f"成功调度 {scheduled_count} 个\n"
        f"失败: {'; '.join(r.reason for r in failed_schedules)}"
    )
else:
    reply = (
        f"任务规划完成: {task_graph.goal}\n"
        f"共 {len(task_graph.tasks)} 个任务, "
        f"全部调度成功"
    )
```

### 2.4 Actual return value

```python
PipelineResult(
    success=True,
    goal="你好",
    reply="任务规划完成: 你好\n共 3 个任务, 全部调度成功",
    task_graph=<TaskGraph 3 tasks>,
    schedule_results=[...],
    audit_log=[...],
)
```

### 2.5 What Gateway receives

```
reply = "任务规划完成: 你好\n共 3 个任务, 全部调度成功"
```

Gateway 期望的是自然语言的 LLM 回复（如 "你好！有什么可以帮助你的？"），但收到的是调度器模板文本。Gateway 无法从中提取有效内容，回退到占位文本。

---

## 3. Root Cause

### 旧 Kernel（参考/已完成项目/总控制面板/app/runtime/kernel.py）

旧 kernel 的 `_execute()` 方法（line 152-218）：

```python
def _execute(self, message, session_id, max_turns, llm_client):
    plan = self.planner.create_plan(message)         # ← 计划

    for turn in range(max_turns):
        raw, last_err = self.scheduler.dispatch(     # ← 调用 LLM
            self.context_engine.build(...),
            llm_client=llm_client)                    # ← 传入 LLM 客户端

        # 解析工具调用
        # 执行工具
        # 累积 final_reply

    if not final_reply:
        final_reply = "收到（母体-小梦已读）"         # ← fallback

    return {"reply": final_reply, "turns": ...}
```

关键：旧 kernel 的 `scheduler.dispatch()` 实际调用了 LLM API，返回 LLM 生成的文本。

### 新 Kernel（app/runtime/kernel.py）

新 kernel 的 `process()` 方法（line 231-390）：

```python
def process(self, message, session_id=0):
    # Governor check
    # Emergency check
    task_graph = self.planner.create_plan(message)       # ← 计划（相同）
    schedule_results = self.scheduler.schedule_graph()   # ← 只分配 Worker，不调 LLM

    reply = f"任务规划完成: {goal}\n共 N 个任务, 全部调度成功"  # ← 模板文本

    return PipelineResult(reply=reply, ...)
```

关键：新 kernel 的 `scheduler.schedule_graph()` **只分配 Worker 到任务，从不调用 LLM API**。

### 差异对照

| | 旧 Kernel (v0.1) | 新 Kernel (v0.3) |
|---|---|---|
| Planner | `create_plan()` ✅ | `create_plan()` ✅ |
| LLM 调用 | `scheduler.dispatch(llm_client=...)` ✅ | **不存在** ❌ |
| 工具执行 | `capability.execute()` ✅ | **不存在** ❌ |
| final_reply | LLM 生成的文本 | 模板: "任务规划完成: ..." |
| fallback | "收到（母体-小梦已读）" | 无（模板永远非空） |

### 根因

**v0.2/v0.3 kernel 重构时，LLM 调用执行循环被 Planner+Scheduler 替代，但没有实现 LLM 文本生成阶段。** 新 kernel 只有"规划"和"调度"，没有"执行"——这是一个只有骨架没有血肉的 pipeline。

---

## 4. 数据流对比

### 旧 Kernel 数据流

```
用户 "你好"
  ↓
Governor (allow)
  ↓
Planner → TaskGraph (3 tasks)
  ↓
Scheduler.dispatch(llm_client=...)  ← 调用 LLM API
  ↓
LLM 返回: "你好！我是小梦，有什么可以帮助你的吗？"
  ↓
final_reply = "你好！我是小梦，有什么可以帮助你的吗？"
  ↓
返回 → Gateway → 用户看到自然语言回复
```

### 新 Kernel 数据流

```
用户 "你好"
  ↓
Governor (allow)
  ↓
Planner → TaskGraph (3 tasks)
  ↓
Scheduler.schedule_graph()  ← 只分配 Worker，不调 LLM
  ↓
reply = "任务规划完成: 你好\n共 3 个任务, 全部调度成功"
  ↓
返回 → Gateway → Gateway 无法解析 → "（母体已处理，无文字回复）"
```

---

## 5. 谁把 reply 变成空字符串？

**reply 本身不是空字符串。** `reply = "任务规划完成: 你好\n共 3 个任务, 全部调度成功"` 是有效的非空字符串。

问题出在 Gateway 层（不在本仓库，在 `/opt/mbclaw/` 生产服务器）：

1. Gateway 调用 `kernel.process("你好")` 得到 `PipelineResult`
2. Gateway 读取 `result.reply` → `"任务规划完成: 你好\n共 3 个任务, 全部调度成功"`
3. Gateway 尝试从中提取 **assistant message** 或 **user-facing content**
4. "任务规划完成" 不是一个有效的对话回复，Gateway 判定为"无有效内容"
5. Gateway 替换为占位文本: `"（母体已处理，无文字回复）"`

---

## 6. 占位文本位置

`"（母体已处理，无文字回复）"` 不在本仓库代码中。

根据旧 kernel 的模式（line 197, 214），占位文本在 Gateway 层的 API handler 中：

```python
# 推测 Gateway 代码（不在本仓库）
result = kernel.process(message, session_id)
reply = result.reply

if not reply or reply.startswith("任务规划完成"):  # ← 系统模板，非用户回复
    reply = "（母体已处理，无文字回复）"
```

---

## 7. 影响范围

所有请求类型都受影响：

| 请求类型 | 期望回复 | 实际回复 | 用户体验 |
|---|---|---|---|
| "你好" | 自然语言问候 | "任务规划完成: 你好\n共 3 个任务..." | 占位文本 |
| "检查服务器状态" | 服务器状态信息 | "任务规划完成: 检查服务器状态\n共 4 个任务..." | 占位文本 |
| "部署新版本" | 部署结果 | "任务规划完成: 部署新版本\n共 4 个任务..." | 占位文本 |

**任何用户请求都不会得到自然语言回复。** 所有请求都返回调度器模板文本。

---

## 8. 修复建议（仅供参考，不执行）

需要在新 kernel 中恢复 LLM 调用执行循环：

1. 在 `Scheduler` 中添加 LLM dispatch 方法
2. 在 `kernel.process()` 的 Phase 3 之后添加 LLM 执行循环
3. 将 LLM 返回的文本作为 `reply` 而不是模板文本
4. 保留 fallback 机制（如果 LLM 返回空）

---

*Root cause analysis by AI agent (OpenHands). No code modified.*
