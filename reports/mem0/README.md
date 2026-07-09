# Mem0 — 参考分析

> Phase 0 Architecture Freeze | 只读分析
> 日期: 2026-07-09

## 项目概述

Mem0 是一个 Memory Layer for AI Agents，提供长期记忆的存储和检索。
核心价值：自动从对话中提取记忆，支持语义检索。

## 架构



## Memory 工作流



## 与 MBclaw Memory 的对比

| 维度 | Mem0 | MBclaw Memory |
|------|------|--------------|
| 检索方式 | Embedding 语义向量 | FTS5 全文 + jieba 关键词 |
| 存储 | 外部向量 DB (Qdrant/...) | SQLite (内置) |
| 依赖 | embedding API + 向量 DB | 零额外依赖 |
| 提取 | LLM 自动提取事实 | LLM 摘要 + jieba 关键词 |
| 部署 | 需要向量 DB 服务 | 单文件 SQLite |
| 规模 | 百万级 | 千级(当前) |

## 可直接复用的设计

1. **记忆更新机制**: add() → update() (而非覆盖) 值得参考
2. **user_id 隔离**: 按用户隔离记忆，比我们按 session 隔离更合理
3. **记忆分类**: category 标签 (preference/fact/instruction) 可用于过滤

## 不适合 MBclaw 的部分

- 依赖外部向量 DB (增加运维复杂度)
- 依赖 embedding API (增加延迟和成本)
- 当前 MBclaw 规模 (<1000 设备) 不需要

## 融合方案

**不建议 Fork/Vendor。建议：未来迁移路径。**

1. 短期: 保持 SQLite + FTS5 (ADR-003 已确认)
2. 中期: 当消息量 >10 万条时，引入 embedding + 向量 DB 作为 B 路召回补充
3. 参考 Mem0 的 add/update/delete 接口设计，包装 MemoryRepo
