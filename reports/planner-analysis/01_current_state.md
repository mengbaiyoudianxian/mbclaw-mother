# 任务一：当前 Planner 盘点

## 结论：MBclaw **没有 Planner**

全文搜索 `goal/task/plan/todo/step/workflow/graph/decompose/subtask` — 零命中（仅 github_list_workflows API 函数名中出现，与规划无关）。

---

## 已有能力（隐式、非结构化）

| 概念 | 存在位置 | 形式 | 级别 |
|------|---------|------|------|
| Turn 计数 | agent.py:114 `while turns < max_turns` | 硬编码上限 | 循环控制 |
| 工具调用顺序 | mother_runtime.py:210 `for turn in range(max_turns)` | LLM 自主决定 | 无结构 |
| max_turns=5 | agent.py:94, mother_runtime.py:161 | 参数 | 防止死循环 |
| tool round 限制 | mother_runtime.py:248 `if turn >= 2: break` | 硬编码 | 限制工具轮数 |
| LLM 隐式规划 | LLM Prompt | 自然语言指令 | 不可靠 |
| thinking 标签 | agent.py:138 `THINK_RE` | LLM 输出的 `<thinking>` 标签 | 仅记录，不解析 |

## 缺失能力

| 能力 | 说明 | 严重度 |
|------|------|--------|
| Goal 分析 | 无法理解用户意图是"单步操作"还是"多步任务" | 🔴 高 |
| Task 分解 | 无法将复杂目标拆为子任务 | 🔴 高 |
| Dependency Graph | 无法处理"先下载 → 再解压 → 再安装"的依赖 | 🔴 高 |
| Priority | 无任务优先级 | 🟡 中 |
| Execution Queue | 无任务队列，一次只处理一个消息 | 🟡 中 |
| Replan | 失败后无法自动调整计划 | 🔴 高 |
| Task State | 无任务状态追踪 (pending/running/done/failed) | 🔴 高 |
| SubTask | 无子任务机制 | 🟡 中 |
| Workflow | 无预定义工作流 | 🟢 低 |
| Progress | 无进度追踪 | 🟢 低 |
| Abort/Resume | 无任务中断/恢复 | 🟡 中 |

## 重复能力

无。没有 Planner，不存在重复。

## 冲突能力

无。

## LLM Prompt 的反规划倾向

```
agent.py AGENT_PROMPT:
"始终用中文回复。短小精炼，三句话以内。"
"每轮最多一个工具。收到工具结果后必须直接回复，禁止继续调用工具。"
```

当前 Prompt **明确禁止多轮工具调用连续规划**。这是故意的设计选择（简化交互），但限制了复杂任务能力。

## 总结

| 指标 | 数值 |
|------|------|
| 结构化 Planner | 0 |
| Goal 分析 | 0 |
| Task 分解 | 0 |
| Dependency | 0 |
| Priority | 0 |
| Queue | 0 |
| Replan | 0 |
| 唯一"规划"来源 | LLM 自身推理（不可靠） |
