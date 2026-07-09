## ADR-008: Compute 无状态执行

Status: Accepted (2026-07-09)

### 决策
Compute 作为无状态执行层，统一管理 shell 执行、HTTP 代理、设备命令。安全过滤在 Compute 层统一拦截。

### 迁移
从 tools.py execute() 的 if-elif 分支提取执行逻辑。
