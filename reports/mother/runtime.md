# Mother Runtime 分析

## 作用

MotherRuntime 是母体的核心运行时引擎，负责 session-aware agent loop。它管理每个会话的 WorkingMemory，接收用户消息后通过 LLM → Tool 循环生成回复。

主要职责：
- 管理会话级 WorkingMemory（每个 session_id 一个实例）
- 构建 LLM 候选 Key 列表（从 TokenPool 获取）
- 执行 Agent Loop：LLM 调用 → 解析 tool → 执行 tool → 反馈结果
- 与 MemoryRepo 集成，在每轮对话中注入相关记忆
- 提供 session 重置能力

## 当前实现

文件：`app/mother_runtime.py`，约 335 行。

### WorkingMemory
- 纯内存上下文，不持久化
- 80% token 阈值自动压缩（截断前半，插入摘要）
- token 估算：字符数 / 4
- 最多保留最近 20 条消息
- 支持记忆注入（recall）

### MotherRuntime
- 全局单例模式
- `_sessions: dict[int, WorkingMemory]` 管理所有会话
- `run()` 方法实现完整的 agent loop（最多 5 轮）
- `_build_candidates()` 从 TokenPool 按优先级构建 LLM Key 列表
- `_execute_tool()` 路由到 skills.py 或 tools.py

### System Prompt
- 硬编码系统提示，包含 42 项技能声明和 14 个工具定义
- 工具用 `<tool>名称</tool><content>参数</content>` 格式
- 支持 `<thinking>` 标签

## 存在问题

1. **单例模式 + 全局 dict**：`_sessions` 存储在进程内存中，无持久化，重启丢失所有会话上下文
2. **WorkingMemory 与 MemoryRepo 两套记忆系统并存**：WorkingMemory 管理短期上下文，MemoryRepo 管理长期记忆，但两者之间缺乏统一的编排层
3. **TokenPool 耦合**：`_build_candidates()` 直接调用 `app.token_pool.get_pool()`，硬编码 provider 优先级列表
4. **LLM 调用无重试/熔断**：候选列表遍历 4 个，失败只是跳过，没有 backoff 策略
5. **session_id 生成方式不一致**：gateway_agent 使用 `hash(code) % 100000`，可能有冲突
6. **与 agent.py 功能重复**：MotherRuntime（mother_runtime.py）和 agent_run（agent.py）都是 agent loop 实现，但相互独立，代码重复
7. **工具解析用正则，非结构化**：`<tool>` 标签解析脆弱，无 schema 校验

## 建议

1. 统一 agent loop 实现，消除 mother_runtime.py 和 agent.py 的重复
2. WorkingMemory 应考虑持久化或至少序列化能力，支持热重启
3. LLM 调用层应抽象为独立 Provider 模块，而非直接使用 TokenPool
4. session_id 生成应使用 UUID 或数据库自增
5. 工具调用格式应升级为结构化 JSON（如 function calling）

## 以后是否保留

**保留，但需要重构**。MotherRuntime 是母体的核心调度引擎，功能正确。但需要：
- 与 agent.py 合并
- TokenPool 调用改为通过 Provider 抽象层
- WorkingMemory 增加持久化
- 工具调用格式升级
