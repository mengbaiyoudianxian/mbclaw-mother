# Claude Code — 参考分析

> Phase 0 Architecture Freeze | 只读分析
> 日期: 2026-07-09
> 仓库: github.com/anthropics/claude-code (插件市场，核心闭源)

## 项目概述

Claude Code 是 Anthropic 的 CLI Agent。仓库公开内容为**插件市场**（TypeScript），核心 Agent 闭源。

## 仓库结构（公开内容）

```
claude-code/
├── .claude-plugin/marketplace.json   插件市场索引
├── plugins/README.md                 插件开发指南
├── scripts/ (TypeScript)
│   ├── auto-close-duplicates.ts      Issue 自动管理
│   ├── issue-lifecycle.ts            Issue 生命周期
│   ├── sweep.ts                      清理脚本
│   └── lifecycle-comment.ts          生命周期评论
└── .devcontainer/                    VS Code Dev Container
```

## 核心设计（基于官方文档 code.claude.com）

### 1. Agent Loop

```
用户输入 → System Prompt (tools + rules + memory)
        → Claude API (streaming)
        → 增量解析 (thinking <-> tool_use 交替)
        → 执行工具 → 结果反馈 → 循环
```

### 2. 上下文压缩（行业标杆）

- 自动检测 token 接近上限
- `/compact` 命令触发手动压缩
- 保留: 关键决策、文件修改摘要、TODO 状态
- 丢弃: 中间工具输出、已解决的错误
- **MBclaw 对照**: WorkingMemory.compress() 只截断，不如 Claude Code 智能

### 3. Checkpoint

```
每轮工具执行前:
    file_snapshot = {path: hash}  (Git 级快照)
    失败/用户拒绝 → 回退文件 + 对话状态
```

### 4. 插件系统

```
.claude-plugin/marketplace.json: 插件注册表
每个插件: hooks + commands + custom agents
```

## 可直接复用的设计

1. **智能压缩**: 按重要性而非时间保留/丢弃 → Context Engine v2
2. **Checkpoint**: 对话状态快照 → Governor checkpoint()
3. **插件注册**: marketplace.json → CapabilityRegistry 动态注册

## 不适合 MBclaw 的部分

- 核心闭源，无法复用代码
- 面向代码开发，非通用 Agent
- 文件 Checkpoint 不适合设备场景

## 融合方案

**无法 Fork（闭源）。参考压缩策略 + Checkpoint 设计。**
