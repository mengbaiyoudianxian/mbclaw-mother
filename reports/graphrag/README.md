# GraphRAG — 参考分析

> Phase 0 Architecture Freeze | 只读分析
> 日期: 2026-07-09

## 项目概述

Microsoft GraphRAG 是一个基于知识图谱的 RAG 系统。
核心价值：从文档中提取实体和关系，构建知识图谱，用图结构增强检索。

## 核心流程



## 与 MBclaw 的关系

| 维度 | GraphRAG | MBclaw |
|------|----------|--------|
| 数据源 | 文档/文本 | 对话消息 |
| 图构建 | 实体+关系提取(LLM) | 无 |
| 检索 | 图遍历 + 社区匹配 | FTS5 + 关键词 |
| 依赖 | LLM提取(贵) + 图DB | SQLite(轻) |
| 适用 | 知识管理/文档Q&A | 个人助理记忆 |

## 可直接复用的设计

1. **关系存储**: experiences 表可增加  字段建立经验之间的关联
2. **层级摘要**: Community Summarization → 按 topic 聚合经验

## 不适合 MBclaw 的部分

- 图构建需要大量 LLM 调用 (成本高)
- Leiden 社区检测需要一定数据量 (当前规模不够)
- 对话记忆 ≠ 文档知识图谱
- 运维复杂度高

## 融合方案

**不建议 Fork/Vendor。仅做远期参考。**

如果以后 MBclaw 需要对跨 session 的知识做关联分析:
1. 在 experiences 表增加 entity 字段
2. 增加 experience_relations 表 (experience_a, experience_b, relation_type)
3. 检索时做 1-hop 图遍历增强召回
