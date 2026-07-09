# FreeLLMAPI — 参考分析

> Phase 0 Architecture Freeze | 只读分析
> 日期: 2026-07-09
> 仓库: github.com/Decentralised-AI/freellmapi (TypeScript, Node.js)

## 项目概述

FreeLLMAPI 聚合 12 家免费 LLM Provider，提供统一 OpenAI-compatible 端点。
**架构与 MBclaw TokenPool 几乎完全一致，但用 TypeScript 实现。**

## 仓库结构

```
freellmapi/
├── server/src/
│   ├── app.ts                    Express 入口
│   ├── providers/                12 家 Provider 适配器
│   │   ├── base.ts               BaseProvider 抽象
│   │   ├── openai-compat.ts      OpenAI 兼容适配器
│   │   ├── google.ts, cohere.ts, cloudflare.ts
│   │   └── index.ts              注册表
│   ├── services/
│   │   ├── router.ts (236行)     核心路由器!
│   │   ├── ratelimit.ts          速率限制
│   │   └── health.ts             健康检测
│   ├── routes/
│   │   ├── proxy.ts              /v1/chat/completions 代理
│   │   ├── fallback.ts           故障转移
│   │   ├── keys.ts               Key 管理
│   │   └── analytics.ts          分析
│   ├── lib/
│   │   ├── crypto.ts             AES 加密
│   │   └── content.ts            内容处理
│   └── middleware/
│       └── errorHandler.ts       错误处理
├── client/                       前端管理面板
├── docs/                         文档
└── package.json                  Node.js 配置
```

## Router 核心逻辑 (router.ts:236行)

```
routeRequest(model, messages):
    1. 查询可用 Keys (SELECT * WHERE enabled AND status != 'rate_limited')
    2. 按 priority 排序 (动态: 429 惩罚 → 降级, 2分钟衰减恢复)
    3. Round-robin 选择 (同 priority 组内轮询)
    4. canMakeRequest()  检查 RPM/RPD
    5. canUseTokens()    检查 TPM/TPD
    6. isOnCooldown()    检查冷却状态
    7. 全部不可用 → 返回 fallback 模型
```

## 与 MBclaw TokenPool 的对比

| 维度 | FreeLLMAPI | MBclaw TokenPool |
|------|-----------|-----------------|
| 语言 | TypeScript (Node.js) | Python (FastAPI) |
| Provider | 12 免费 API | 4 免费 + 商业 + MiClaw |
| Router | 236行 router.ts | scheduler.py + caller.py |
| 限流 | RPM/RPD/TPM/TPD | 四轴滑动窗口 + 阶梯冷却 |
| 降级 | 429 惩罚 (2分钟衰减) | 阶梯冷却 (2m→10m→1h→24h) |
| 故障转移 | round-robin | 顺序遍历 candidates[:max_retries] |
| 计费 | 无 | sold_keys 倍率+余额 |
| Key 加密 | AES | AES-256-GCM |
| 数据库 | SQLite (better-sqlite3) | SQLite (sqlalchemy) |
| 管理面板 | client/ (React) | 嵌入式 HTML |

## 核心差异

### FreeLLMAPI 优势
- **动态优先级**: 429 自动降级 + 衰减恢复 (TokenPool 用固定阶梯)
- **Round-robin**: 同优先级轮询 (TokenPool 顺序遍历)
- **轻量**: 236 行 router vs TokenPool 的 scheduler+caller+health

### TokenPool 优势
- **评分为主**: 三维评分(可靠性/速度/能力)做选择 (FreeLLMAPI 仅 priority 排序)
- **故障转移更强**: 熔断+阶梯冷却 (FreeLLMAPI 仅 round-robin)
- **商业化**: 计费系统 (FreeLLMAPI 无)
- **MiClaw 集成**: 免费代理通道

## 可直接复用的设计

1. **动态 429 惩罚**: 替换 TokenPool 的固定阶梯冷却 → 更灵活
2. **Round-robin**: 同分 Provider 轮询 → 比顺序遍历更均衡
3. **轻量 Router**: 236 行 vs TokenPool 的 3 层调度

## 融合方案

**不建议 Fork/Vendor。建议：借鉴 Router 算法改进 TokenPool。**

1. TokenPool Scheduler 增加动态 429 惩罚机制 (当前是固定阶梯)
2. TokenPool Caller 增加 round-robin 同分组轮询 (当前是顺序遍历)
3. 不引入 Node.js, 保持 Python 技术栈统一
