# Codex CLI — 参考分析

> Phase 0 Architecture Freeze | 只读分析
> 日期: 2026-07-09
> 仓库: github.com/openai/codex (Rust 重写)

## 项目概述

Codex CLI 是 OpenAI 的命令行 Agent。核心已从 TypeScript 迁移至 **Rust** (`codex-rs/`)。
仓库公开，但执行策略(exec policy)和沙箱细节部分闭源。

## 仓库结构

```
codex-cli/
├── codex-rs/                    Rust 核心
│   ├── Cargo.toml               Rust 项目配置
│   ├── cli/                     CLI 入口
│   ├── skills/                  技能系统
│   ├── bwrap/                   Bubblewrap 沙箱
│   ├── linux-sandbox/           Linux 沙箱
│   ├── windows-sandbox-rs/      Windows 沙箱
│   └── execpolicy-legacy/       执行策略(旧)
├── scripts/                     Python 脚本
└── announcement_tip.toml        公告配置
```

## 核心设计

### 1. Rust 重写架构

```
codex-rs/
├── cli/           CLI 入口 (参数解析、交互循环)
├── skills/        技能系统 (.codex/skills 目录)
├── bwrap/         Bubblewrap 容器隔离 (Linux)
├── linux-sandbox/ Linux 沙箱策略
├── windows-sandbox-rs/ Windows 沙箱
└── execpolicy-legacy/ 执行策略 (允许/拒绝命令)
```

### 2. 沙箱隔离

Codex CLI 的独特设计:
- Bubblewrap (bwrap) 容器隔离
- 执行策略: 每命令需要审批
- 跨平台: Linux/Windows 不同沙箱实现
- **MBclaw 对照**: Compute.run_command() 只有黑名单过滤，无沙箱

### 3. 技能系统

```
.codex/skills/ 目录:
    每个技能 = Rust 编译的 .wasm 或配置文件
    支持 build.rs 编译时注入
```

## 可直接复用的设计

1. **执行策略**: 命令审批机制 (allow/deny/ask) → Compute 安全增强
2. **技能编译注入**: build.rs 编译时注册 → Capability 静态注册

## 不适合 MBclaw 的部分

- Rust 重写 (MBclaw 是 Python)
- 沙箱隔离 (移动设备不需要 Docker/bwrap 级别隔离)
- 面向代码开发

## 融合方案

**不建议 Fork/Vendor。参考执行策略设计。**

Compute 增加命令审批级别:
- allow: 白名单命令自动执行
- ask: 需要用户确认
- deny: 黑名单命令拒绝
