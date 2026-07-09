# OpenHands — 参考分析

> Phase 0 Architecture Freeze | 只读分析
> 日期: 2026-07-09

## 项目概述

OpenHands v0.36+ 已拆分为两层架构:
1. **openhands-sdk** (Python 包): Agent Runtime、LLM、Conversation、Tools
2. **Server** (当前仓库): App Server、Sandbox、Auth、Integrations

## 架构层次



## 与 MBclaw Mother 的对比

| 维度 | OpenHands | MBclaw Mother |
|------|-----------|---------------|
| Agent 模式 | 通用 (code/chat/browse) | 个人助理 (device/shell/chat) |
| 沙箱 | Docker/K8s 隔离 | 本地进程 (无沙箱) |
| LLM Provider | SDK 内置 | TokenPool 外部服务 |
| 工具系统 | SDK 插件式 | 静态注册 |
| 扩展性 | 高 (sandbox + integrations) | 低 (进程内) |
| 部署 | 服务端 + Sandbox | 单进程 |

## 可直接复用的设计

1. **SDK/Server 分离**: 将 Agent Runtime 作为独立包，Server 只做 Web 层
   → MBclaw 可以考虑  包 + Server
2. **依赖注入**: services/injector.py 的 Injector 模式
   → Governor 可以用 DI 管理 Coordinator/Planner/Scheduler 实例
3. **Integrations 层**: GitHub/GitLab/Bitbucket 适配器
   → 比我们 skills.py 的 GitHub 函数更规范化

## 不适合 MBclaw 的部分

- Sandbox 机制过于复杂 (不需要 Docker 隔离)
- 面向开发者工具 (code agent)，不是个人助理
- SDK 重量级，引入大量依赖

## 融合方案

**不建议 Fork/Vendor。建议：参考架构分层。**

1. 参考 SDK/Server 分离 → MBclaw 的目标架构已类似 (mother/ 包 + main.py)
2. 参考 Injector 模式 → Governor 初始化用 DI
3. 参考 Integrations 层 → Capability 的 GitHub/SSH 可参考

## 建议

参考架构分层和依赖注入设计。不引入代码。
