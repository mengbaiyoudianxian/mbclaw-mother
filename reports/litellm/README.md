# LiteLLM — 参考分析

> Phase 0 Architecture Freeze | 只读分析
> 日期: 2026-07-09

## 项目概述

LiteLLM 是一个统一的 LLM Provider 抽象层，支持 100+ LLM API 的统一调用格式（OpenAI 兼容）。
核心价值：一个  调用适配所有 Provider。

## 架构



## 可直接复用的设计

### 1. Router — 多 Key 故障转移



**MBclaw 对照**: 我们的 Scheduler 模块可以参考此模式。
TokenPool 已实现类似功能(call_with_fallback)，但 Mother 绕过了它。

### 2. Provider 抽象 — BaseLLM

所有 Provider 继承统一的 BaseLLM，实现:
-  /  / 
- 统一异常映射 (RateLimitError, ContextWindowExceededError, ...)
- 统一日志 + 回调

### 3. 成本计算 + 预算

每个请求自动计算成本 ($)，支持预算上限。TokenPool 的 sold_keys 有倍率但没有类似机制。

## 不适合 MBclaw 的部分

- LiteLLM 太庞大 (66KB __init__.py, 300+ 文件)
- 支持 100+ Provider，MBclaw 只需 5-8 个
- 有完整的 proxy 服务器 (与 TokenPool 功能重叠)
- 开销: 额外抽象层带来 ~5-10ms 延迟

## 融合方案

**不建议 Fork/Vendor。建议：仅参考设计。**

1. 参考  的多 Key 故障转移逻辑 → 融入 TokenPool Scheduler
2. 参考  的统一异常映射 → 融入 TokenPool Caller
3. 参考  → 融入 TokenPool 计费

## 建议

仅参考设计，不引入依赖。LiteLLM 太重，MBclaw 应保持轻量。
