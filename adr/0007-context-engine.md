## ADR-007: Context Engine 独立

Status: Accepted (2026-07-09)

### 决策
Context Engine 从 MotherRuntime 中独立出来，提供纯粹的上下文管理。Governor 不管理上下文细节。

### 迁移
WorkingMemory 类从 mother_runtime.py:8-59 完整迁移到 context_engine 模块。
