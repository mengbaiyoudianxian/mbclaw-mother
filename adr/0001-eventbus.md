## ADR-001: 事件驱动架构

Status: Accepted (2026-07-09)

### 决策
采用进程内 EventBus，模块间通过发布/订阅事件通信。Governor 作为编排者，显式管理异步流程。

### 事件类型
session.*, memory.*, tool.*, llm.*, scheduler.fallback, runtime.error

### 后果
正面: 模块解耦可测试。负面: 调试复杂度增加。
