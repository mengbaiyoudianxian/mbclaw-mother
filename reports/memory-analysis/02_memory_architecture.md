# 任务二：Memory 架构分析

## 当前架构（两层）

```
┌─────────────────────────────────────────┐
│              调用层                      │
│  MotherRuntime  │  pipeline.py  │  api.py │
│  wm.set_recall  │ close_session │ query   │
└────────┬────────┴───────┬───────┴────┬────┘
         │                │            │
         ▼                ▼            ▼
┌─────────────────────────────────────────┐
│          MemoryRepo (逻辑层)             │
│  query()          dual-recall           │
│  write_session_memory()                 │
│  query_experiences()                    │
│  render_injection_for_new_session()     │
│  _maybe_evict_experiences()             │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│           数据层 (5+2 表)                │
│  sessions │ messages │ summaries         │
│  keywords │ experiences                  │
│  messages_fts │ experiences_fts (虚拟表)  │
└─────────────────────────────────────────┘
```

## 逻辑层分析

| 函数 | 输入 | 输出 | 职责 |
|------|------|------|------|
| `query(q, top_n)` | 查询文本 | [MemoryHit] | 双路召回: FTS5 + jieba |
| `write_session_memory(...)` | session_id + 摘要/关键词/经验 | None | 原子写入 |
| `query_experiences(q, top_n)` | 查询文本 | [Experience] | FTS5 经验搜索 + 种类加分 |
| `render_injection_for_new_session()` | 排除 session_id | str or None | 新会话注入: 上次事实+失败+成功 |
| `_maybe_evict_experiences()` | — | int (归档数) | 超 1000 条 → JSONL 归档 |

## 数据层分析

| 表 | 存储内容 | 索引 | 淘汰策略 |
|-----|---------|------|---------|
| sessions | 会话元数据 (状态/时间) | PK id | 不淘汰 |
| messages | 对话全文 (role+content) | PK id, FTS5 content | 不淘汰 (SQLite 无限增长) |
| summaries | 会话 LLM 摘要 | PK id, UNIQUE session_id | 覆写 (1 session = 1 summary) |
| keywords | jieba 关键词 + 权重 | PK id, FK session_id | 覆写 (delete + re-insert) |
| experiences | LLM 提取经验 | PK id, FTS5 title+content | >1000 → JSONL 归档 |

## 是否独立？与 Context Engine 混合？

```
当前状态: MemoryRepo 是独立模块 ✅
  - memory.py (独立文件)
  - 自己的数据模型 (MemoryHit)
  - 自己的 FTS5 SQL
  - 不依赖 Context Engine

但是: WorkingMemory (在 mother_runtime.py) 混入了 Context 职责 ❌
  - WorkingMemory.set_recall() ← 调 MemoryRepo.query()
  - WorkingMemory.to_messages() ← 拼接 recall 到 system message

结论: Memory 数据层独立，但 Context 层 (WorkingMemory) 与 Memory 召回混合。
```

## 当前评分算法

```
score = 0.6 * (fts_score / fts_max) + 0.4 * (keyword_match / kw_max)
```

- FTS5: 基于 BM25 的 rank
- Keyword: jieba 分词 → keywords 表 IN 匹配
- FTS 权重 > Keyword 权重 (0.6 vs 0.4)
- 无语义相似度、无词向量、无时间衰减
