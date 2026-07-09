# OpenClaw — 参考分析

> Phase 0 Architecture Freeze | 只读分析
> 日期: 2026-07-09
> 仓库: github.com/openclaw/openclaw (TypeScript, 21k+ 文件)

## 项目概述

OpenClaw 是一个全栈 AI Agent 平台，包含移动端 App (Android/iOS/macOS) + 服务端。
远不止 Gateway——它是一个完整的 Agent 操作系统。

## 仓库结构

```
openclaw/
├── apps/
│   ├── android/          Android App
│   ├── ios/              iOS App
│   ├── macos/            macOS App (+ MLX TTS)
│   └── shared/           跨平台共享代码
├── src/                  服务端核心 (1000+ 文件)
│   ├── channels/         多渠道系统 (核心!)
│   │   ├── registry.ts   渠道注册表
│   │   ├── session.ts    会话管理
│   │   ├── streaming.ts  流式回复
│   │   ├── turn/         对话轮次
│   │   ├── thread-bindings/ 线程绑定
│   │   ├── plugins/      渠道插件
│   │   ├── transport/    传输层
│   │   └── message/      消息格式
│   ├── agents/           Agent 系统
│   │   └── tools/        gateway.ts, gateway-tool.ts
│   ├── context-engine/   上下文引擎
│   │   ├── init.ts, registry.ts
│   │   ├── delegate.ts, types.ts
│   │   └── runtime-settings.ts
│   ├── daemon/           守护进程
│   ├── commands/         命令系统
│   ├── config/           配置管理
│   └── cron/             定时任务
├── config/               TypeScript 配置
├── deploy/               Docker 部署
├── docs/                 文档
└── .agents/skills/       30+ Agent 技能
```

## 关键设计

### 1. Channels 系统 (100+ 文件)

```
channels/ 架构:
    registry.ts       渠道注册: normalizeChannelId(), listRegisteredChannelPluginIds()
    session.ts        会话: 跨渠道绑定
    streaming.ts      流式: draft-stream 控制
    turn/             对话轮次管理
    thread-bindings/  线程绑定 (用户↔渠道)
    plugins/           渠道插件 (channel-id.types, types.core)
    transport/         传输层 (多协议)
    message/           消息格式 (inbound-event)
```

**MBclaw 对照**: 我们的 Gateway 只有 7 个 Adapter + 1 个 thin forwarder。
OpenClaw 的 channels/ 是一个完整的消息操作系统。

### 2. Context Engine

```
context-engine/
├── init.ts            引擎初始化
├── registry.ts        上下文注册
├── delegate.ts        委托/代理
├── types.ts           类型定义
├── runtime-settings.ts 运行时配置
├── host-compat.ts     宿主兼容层
└── quarantine-health.ts 隔离健康检查
```

**MBclaw 对照**: 我们的 Context Engine 目前只有一个 WorkingMemory 类。
OpenClaw 有完整的引擎生命周期管理。

### 3. Agent 技能系统

```
.agents/skills/ (30+ 技能):
├── clawdtributor        代码贡献
├── clawsweeper          代码清理
├── discord-clawd        Discord 集成
├── openclaw-qa-testing   QA 测试
├── openclaw-pr-maintainer PR 维护
├── control-ui-e2e        UI E2E 测试
├── agent-transcript     对话记录
└── ...
```

每个技能是一个独立的 Agent 配置文件，可独立调用。

## 与 MBclaw 的对比

| 维度 | OpenClaw | MBclaw Mother |
|------|----------|---------------|
| 语言 | TypeScript | Python |
| 规模 | 21k+ 文件 | ~70 有效文件 |
| 移动端 | Android/iOS/macOS | Android APK (独立) |
| 渠道 | channels/ (100+ 文件) | Gateway (7 适配器) |
| 上下文 | context-engine/ (8 文件) | WorkingMemory (1 类) |
| 技能 | 30+ Agent 技能 | 25 工具 + 35 技能 |
| 部署 | Docker + 移动端 | 单进程 FastAPI |

## 可直接复用的设计

1. **渠道插件化**: channels/plugins/ → Gateway 改为插件注册模式
2. **Context Engine 独立**: 独立模块 + registry → 我们已规划但未实现
3. **技能即 Agent**: 每个技能是独立 Agent 配置 → Capability prompt_skill
4. **Thread Bindings**: 用户↔渠道绑定 → Session 增加 channel 字段

## 不适合 MBclaw 的部分

- TypeScript 全栈 (MBclaw 是 Python)
- 规模过大 (21k 文件 vs 70 有效文件)
- 移动端 App (MBclaw 已有独立 APK)

## 融合方案

**不建议 Fork/Vendor。参考 Channels 插件化 + Context Engine 架构。**

1. Gateway: 参考 registry.ts 的插件注册模式
2. Context Engine: 参考 context-engine/ 的模块化设计
3. Capability: 参考 .agents/skills/ 的声明式技能定义
