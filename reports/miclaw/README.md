# MiClaw — 参考分析

> Phase 0 Architecture Freeze | 只读分析
> 日期: 2026-07-09
> 注意: MiClaw 是 MBclaw 已有的第三方服务（端口 8765），非外部参考项目。此分析基于 MBclaw 代码中对 MiClaw 的使用。

## 项目概述

MiClaw 是一个 LLM API 免费代理服务，为 MBclaw 提供低成本的 LLM 调用通道。

## 在 MBclaw 中的角色

```
Mother/Control Panel
    │
    ├── bridge_manager.py → 管理 MiClaw 实例 (创建/销毁/暂停/登录)
    ├── bridge_login.html → MiClaw 登录页面
    └── /bridge/miclaw/*  → HTTP 代理到 MiClaw API
```

## 核心功能

### 1. 账户管理

```
miclaw_accounts 表 (pool.db):
    ├── 手动添加账户
    ├── Bridge 登录验证
    └── 借用白名单 (borrow_allowed_users)
```

### 2. 实例管理

```
bridge_manager.py:
    ├── POST /apply  → 创建实例记录
    ├── POST /login  → 验证凭证(调 MiClaw API)
    ├── POST /destroy → 销毁实例
    ├── POST /pause  → 暂停实例
    ├── GET  /status → 轮询登录状态
    └── ANY  /v1/*   → LLM 代理透传
```

### 3. LLM 代理

```
POST /bridge/miclaw/v1/chat/completions
    → bridge_manager 透传
    → MiClaw API
    → 返回响应
```

## 与 TokenPool 的关系

| 维度 | TokenPool | MiClaw |
|------|-----------|--------|
| 定位 | Key 管理 + 调度 | 免费代理通道 |
| Key 来源 | 手动/心跳/购买 | 桥接账户 |
| 计费 | 有 (sold_keys) | 免费 |
| 稳定性 | 高 (多 Key 故障转移) | 低 (依赖代理稳定性) |
| 用途 | 主力 LLM 调用 | 备用/低成本通道 |

## 存在的问题

1. **Bridge 无鉴权**: /bridge/miclaw/* 路由无鉴权，任何人都可创建实例
2. **与 TokenPool 并行**: Mother 同时用 TokenPool 和 MiClaw，两条路径
3. **实例状态不持久化**: miclaw_instances.json 存 JSON，非数据库
4. **与 Scheduler 的集成**: 应作为 TokenPool 的一个 Provider 类型，而非独立路径

## 融合方案

**保留 MiClaw 作为 TokenPool 的一个 Provider。**

```
当前:  Mother → bridge_manager → MiClaw (独立路径)
目标:  Mother → Scheduler → TokenPool → MiClaw Provider (统一路径)
```

MiClaw 不应是 Mother 直连的独立通道，而应注册为 TokenPool 的一个 Provider 类型。
TokenPool 接到请求后，根据 task_type 决定是否使用 MiClaw (low_cost 策略)。
