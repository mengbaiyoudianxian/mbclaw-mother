# Mother Agent 分析

## 作用

agent.py 是母体的另一个 agent loop 实现，提供 LLM-driven 对话循环与工具执行。与 mother_runtime.py 功能重叠但实现不同：agent.py 更早出现，依赖数据库 Session/Message 模型，使用 LLMClient 直接调用。

主要职责：
- agent_run()：基于数据库 Session 的 agent loop
- MotherAgent 类：面向多渠道消息的简化处理
- get_mother()：懒加载单例

## 当前实现

文件：`app/agent.py`，约 204 行。

### agent_run()
- 入参：数据库 session、session_id、用户消息、LLMClient
- 从数据库加载对话历史（最近 10 条）
- 从数据库加载工具列表
- LLM 调用（直接用 httpx，不走 LLMClient.chat）
- 最多 5 轮 agent loop
- 每轮结果写入数据库 Message 表
- 支持 MBCLAW_LLM_MOCK 模式

### MotherAgent
- 极简实现：直接调用 LLMClient.chat()，单轮
- 不支持工具调用
- 不支持记忆
- enqueue() 始终返回 True（空实现）

### 与 MotherRuntime 的关键差异
| 特性 | agent_run | MotherRuntime.run |
|------|-----------|-------------------|
| 消息存储 | 数据库 Message 表 | 内存 WorkingMemory |
| 记忆注入 | MemoryRepo + 对话历史 | MemoryRepo + recall |
| LLM 调用 | 单 LLMClient | 多候选（TokenPool） |
| 工具执行 | app.tools.execute | app.tools + app.skills |
| 上下文压缩 | 无 | WorkingMemory 80%阈值压缩 |

## 存在问题

1. **两套 agent loop 并存**：agent_run 和 MotherRuntime.run 是两套独立实现，功能大量重叠
2. **MotherAgent 基本是空壳**：enqueue() 返回 True 但什么都不做，send() 是最简单轮调用
3. **agent_run 中 LLM 调用不一致**：直接用 httpx 而非 LLMClient.chat()，绕过了 TokenPool fallback 逻辑
4. **重复的工具列表构建**：agent_run 和 MotherRuntime 各自构建工具提示
5. **get_mother() 单例几乎不被使用**：实际运行时走的是 gateway_agent → MotherRuntime

## 建议

1. 废弃 agent_run()，统一使用 MotherRuntime
2. 废弃 MotherAgent，gateway_agent 已直接使用 MotherRuntime
3. 如果保留多渠道支持，应在 MotherRuntime 层面统一处理

## 以后是否保留

**不保留**。agent.py 应整体废弃：
- agent_run() → 合并入 MotherRuntime
- MotherAgent → 删除（功能已被 gateway_agent + MotherRuntime 取代）
- StandardMessage dataclass → 如需要，移至 models.py
