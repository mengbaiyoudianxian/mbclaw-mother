# MCP SDK — 参考分析

> Phase 0 Architecture Freeze | 只读分析
> 日期: 2026-07-09

## 项目概述

MCP (Model Context Protocol) 是 Anthropic 提出的标准化协议，用于 AI 模型与外部工具/数据源之间的通信。
Python SDK 实现 Client/Server 模式。

## 架构



## 与 MBclaw Capability 的对比

| 维度 | MCP | MBclaw Capability |
|------|-----|-------------------|
| 协议 | JSON-RPC 2.0 标准化 | 自定义 register/execute |
| 发现 | tools/list 动态发现 | register() 静态注册 |
| 传输 | stdio/SSE/WS 多协议 | 进程内直接调用 |
| 生态 | 100+ MCP Servers | 自建工具 |
| 复杂度 | Client/Server 双端 | 单端 Registry |

## 可直接复用的设计

1. **工具描述格式**: MCP 的 Tool Definition (name, description, inputSchema) 可以作为 CapabilityDef 的参考
2. **自动发现**: tools/list 协议 → CapabilityRegistry.list() 已有类似实现

## 不适合 MBclaw 的部分

- MCP 是 Client/Server 远程协议，MBclaw 的 Capability 都是进程内的
- 引入 MCP 协议增加序列化/网络开销
- 当前不需要远程工具调用

## 融合方案

**不建议 Fork/Vendor。建议：参考协议格式。**

1. CapabilityDef 格式对齐 MCP Tool Definition (便于后续扩展)
2. 如果以后需要远程工具 (如部署到独立 Worker)，再引入 MCP 协议

## 建议

仅参考协议格式做接口对齐。不引入依赖。
