# 任务六：Memory 目录设计

```
memory/
├── __init__.py          导出 MemoryManager
│
├── manager.py           Memory 管理器（统一入口）
│   class MemoryManager:
│       query(msg, top_n, memory_types) → [MemoryHit]
│       write(memory_type, data)
│       get_by_id(memory_type, id) → MemoryEntry
│       list_by_type(memory_type, filters) → [MemoryEntry]
│       职责: 所有 Memory 操作的统一入口
│       替代: 当前 MemoryRepo (扩展为多类型)
│
├── types/               Memory 类型定义 (每层一个文件)
│   ├── __init__.py
│   ├── base.py          BaseMemory (id, created_at, updated_at)
│   ├── conversation.py  ConversationMemory (summary + keywords)
│   ├── project.py       ProjectMemory (name, description, rules, decisions)
│   ├── decision.py      DecisionMemory (title, context, options, chosen, outcome)
│   ├── experience.py    ExperienceMemory (kind, title, content)
│   ├── knowledge.py     KnowledgeMemory (title, content, source, tags, confidence)
│   ├── user_profile.py  UserMemory (user_id, preferences, habits, devices)
│   ├── capability.py    CapabilityMemory (success_rate, avg_latency, best_params)
│   ├── observation.py   ObservationMemory (event_type, device, before, after)
│   └── evolution.py     EvolutionMemory (change_type, before, after, reason)
│       职责: 每种 Memory 类型的 Schema 定义
│       来源: 替代当前 models.py 的单一 Experience/Summary/Keyword 定义
│       部分新建 (Project/Decision/Knowledge/User/Capability/Observation/Evolution)
│
├── storage/             Storage 层（CRUD + Search）
│   ├── __init__.py
│   ├── sqlite_store.py  SQLite CRUD 操作
│   │   class SQLiteStore:
│   │       insert(memory)
│   │       update(memory)
│   │       delete(memory)
│   │       query_by_type(memory_type, filters)
│   │       职责: 数据持久化
│   │       来源: 替代当前 MemoryRepo.write_session_memory()
│   │
│   ├── fts_index.py     FTS5 全文索引管理
│   │   class FTSIndex:
│   │       search(table, query, limit) → [row]
│   │       rebuild()
│   │       职责: FTS5 搜索 (已有, 提取独立)
│   │       来源: 当前 messages_fts + experiences_fts 的 SQL
│   │
│   └── vector_store.py  Vector Store (远期)
│       class VectorStore:
│           add(id, embedding, metadata)
│           search(embedding, k) → [id, score]
│           职责: 语义搜索
│           新功能
│
├── embedding/           Embedding 引擎 (远期)
│   ├── __init__.py
│   └── embedder.py      Text → Vector
│       class Embedder:
│           embed(text) → [float]
│           batch_embed(texts) → [[float]]
│           职责: 文本转向量
│           新功能 (当前只有 FTS5 关键词搜索)
│
├── ranking/             Ranking 层
│   ├── __init__.py
│   ├── scorer.py        评分引擎
│   │   class Scorer:
│   │       score(query, hits) → [(hit, score)]
│   │       策略:
│   │         FTS5 BM25:  0.40
│   │         Keyword:    0.30
│   │         Recency:    0.15 (时间衰减)
│   │         Importance: 0.15 (kind priority)
│   │       职责: 多因子评分 + 排序
│   │       来源: 替代当前 query() 中的简单评分
│   │
│   └── reranker.py      LLM 重排序 (远期)
│       职责: 搜索结果 → LLM 精选 top-N
│
├── retriever/           Retriever 层
│   ├── __init__.py
│   ├── keyword_retriever.py  jieba 关键词检索
│   │   class KeywordRetriever:
│   │       retrieve(query, top_n) → [hit]
│   │       职责: 关键词匹配
│   │       来源: 提取当前 query() 的 B 路
│   │
│   ├── fts_retriever.py  FTS5 全文检索
│   │   class FTSRetriever:
│   │       retrieve(query, memory_types, top_n) → [hit]
│   │       职责: FTS5 搜索
│   │       来源: 提取当前 query() 的 A 路
│   │
│   └── vector_retriever.py  Vector 检索 (远期)
│       职责: 语义搜索
│
├── cleanup/             清理层
│   ├── __init__.py
│   ├── evictor.py       淘汰引擎
│   │   class Evictor:
│   │       evict(memory_type, max_count) → archived_count
│   │       archive(to_path)
│   │       职责: 超量淘汰 + JSONL 归档
│   │       来源: 替代当前 _maybe_evict_experiences()
│   │
│   └── scheduler.py     Cleanup 调度
│       class CleanupScheduler:
│           schedule(interval) → 定期清理
│           职责: 定时清理任务
│           新功能
│
└── pipeline.py          Session-close pipeline
    class MemoryPipeline:
        close_session(db, sid, llm) → result
        职责: Session 关闭时 LLM 总结 → 写入多类 Memory
        来源: 替代当前 pipeline.py close_session()
        扩展: 不只写 Conversation Memory, 还要提取 Project/Decision/Knowledge
```

## 模块依赖

```
MemoryManager
    │
    ├── types/          (Schema 定义) ← ORM Models
    ├── storage/        (CRUD + FTS)  ← SQLAlchemy
    ├── retriever/      (关键词 + FTS + Vector)
    ├── ranking/        (评分 + 排序)
    ├── embedding/      (文本→向量, 远期)
    └── cleanup/        (淘汰 + 归档)
```

## 与当前 memory.py 的映射

| 当前 | 新设计 |
|------|--------|
| MemoryRepo | MemoryManager (统一入口) |
| MemoryRepo.query() | retriever/ + ranking/ |
| MemoryRepo.write_session_memory() | storage/sqlite_store.py |
| MemoryRepo.query_experiences() | retriever/fts_retriever.py |
| MemoryRepo.render_injection_for_new_session() | ContextEngine (非 Memory) |
| MemoryRepo._maybe_evict_experiences() | cleanup/evictor.py |
| pipeline.close_session() | pipeline.py (扩展) |
| 单一 Memory 类型 | types/ 9 种 Memory |
