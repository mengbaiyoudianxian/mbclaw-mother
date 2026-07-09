# 任务二：OpenHands Planner 分析

## 核心发现

OpenHands v0.36+ Agent Runtime 在 `openhands-sdk`（外部包）中。
仓库只暴露 Server 层接口。规划相关组件如下：

## OpenHands 规划相关组件

### 可借鉴（Server 层可见）

| 文件 | 类/函数 | 借鉴什么 | 为什么 |
|------|---------|---------|--------|
| `app_server/app_conversation/app_conversation_start_task_service.py` | `AppConversationStartTaskService` | Task 生命周期接口: search/count/get/save/delete | 作为 Planner 的 TaskRepo 抽象参考 |
| `app_server/app_conversation/app_conversation_models.py` | `ConversationTrigger` (Enum) | 触发类型: RESOLVER/GUI/SUGGESTED_TASK/SLACK/JIRA | Planner 的触发源分类 |
| `app_server/event_callback/event_callback_models.py` | `EventCallbackProcessor` | 事件回调处理 | Planner 执行后的回调通知 |
| `app_server/services/injector.py` | `Injector` | 依赖注入 | Planner → Scheduler 注入 |

### 属于 SDK（不可见，仅推断）

| 组件 | 推测功能 | MBclaw 对应 |
|------|---------|------------|
| `Agent.run()` | Agent Loop | runtime/loop.py |
| `Task` model | 任务定义 | planner/task.py |
| `SubTask` split | 子任务分解 | planner/task_graph.py |
| `Observation` | 观察模型 | runtime/observation.py |
| `ReAct` loop | Reasoning + Acting | 当前 LLM 自行处理 |

### 不能借鉴

| 组件 | 原因 |
|------|------|
| Sandbox 相关 Task | Sandbox 环境任务 — MBclaw 不需要 |
| SuggestedTask | 自动建议任务 — MBclaw 用户主动发起 |
| Jira/Slack 集成 | 外部系统集成 — 不属于 Planner |
| Microagent Management | 微代理管理 — 太复杂 |

## Governor vs Runtime 边界（重申）

```
Planner:   目标→分解→依赖→优先级→队列
Governor:  权限→风险→决策→审计
Runtime:   执行流程→LLM→工具→回复
Scheduler: LLM Provider 选择→调用→故障转移
```

## 迁移成本

0 天（设计参考，不迁移代码）

## 推荐指数

★★☆☆☆ — OpenHands SDK 的 Task 设计不可见，Server 层参考价值有限
