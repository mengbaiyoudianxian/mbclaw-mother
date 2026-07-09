# 任务二：OpenHands Runtime 分析

## 核心发现

OpenHands v0.36+ 将 Agent Runtime 抽离为独立 Python 包 `openhands-sdk`。
服务器仓库只包含 App Server 层。**Agent Loop 在 SDK 中，不在本仓库。**

## Agent Loop 设计（从现有代码还原）

```
openhands-sdk (外部包):
  Agent.run()
    while turns < max_turns:
      Condenser.condense(history)   → 压缩上下文
      LLM.completion(messages+tools) → 调用 LLM
      parse response
        tool_calls → ToolRegistry.execute() → 结果追加
        text → done (最终回复)
      checkpoint (可选)
    return result
```

## 可直接借鉴

| 设计 | 说明 | MBclaw 应用 |
|------|------|------------|
| Condenser | 智能压缩：按重要性而非时间截断 | ContextEngine.compress() 当前 WorkingMemory 只按时间截断 |
| Turn 计数+上限 | 防止无限循环 | 已有 max_turns=5 |
| Tool Result 作为上下文 | 工具结果追加到 messages（非独立存储） | 部分实现 |
| SDK/Server 分离 | Runtime 作为独立包 | 远期目标 |
| Injector 依赖注入 | 服务实例管理 | Governor 初始化用 |

## 不能借鉴

- Sandbox Agent: 需要 Docker/K8s，MBclaw 是个人助理
- Workspace 管理: 文件系统操作，MBclaw 不需要
- Task Agent 子任务分解: 太复杂

## 迁移成本

0 天（设计验证，不迁移代码）

## 推荐指数

★★★★☆ — 验证了 MBclaw Agent Loop 设计正确性。Condenser 是唯一值得引入的设计。
