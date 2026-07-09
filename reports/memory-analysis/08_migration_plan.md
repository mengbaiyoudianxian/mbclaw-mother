# 任务八：Memory 迁移计划

---

## Phase 1 — 统一 Memory Schema（1 天）

### 目标
从单一 Memory 类型 → 多类型 Memory Schema

### 新增
```
memory/__init__.py
memory/types/__init__.py
memory/types/base.py                 ← BaseMemory
memory/types/conversation.py         ← 映射 summaries + keywords
memory/types/experience.py           ← 映射 experiences
```

### 修改
```
memory.py MemoryRepo → memory/manager.py MemoryManager
  - query() 改为多类型路由: query(msg, top_n, memory_types=["conversation", "experience"])
  - write() 改为 write(memory_type, data)
```

### Phase 1 完成标准
- MemoryManager 替代 MemoryRepo
- 支持多 Memory 类型查询
- 向后兼容现有 API
- 数据库表不变 (复用 sessions/summaries/keywords/experiences/messages)

---

## Phase 2 — User Memory（1 天）

### 目标
用户画像存储

### 新增
```
memory/types/user_profile.py         ← UserMemory Schema
memory/storage/sqlite_store.py       ← SQLiteStore
```

### 数据库
```
CREATE TABLE user_profiles (
    id INTEGER PRIMARY KEY,
    user_id TEXT UNIQUE NOT NULL,     -- device code / qq / wx
    preferences JSON DEFAULT '{}',     -- {language, timezone, model_preference, ...}
    habits JSON DEFAULT '{}',         -- {常用命令, 活跃时段, ...}
    devices JSON DEFAULT '[]',        -- [{code, model, brand, last_seen}]
    stats JSON DEFAULT '{}',          -- {total_sessions, total_messages, ...}
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

### Phase 2 完成标准
- 新用户自动创建 profile
- 对话中检测偏好 → 更新 user_profiles
- Context Engine 加载用户偏好注入 Layer 3

---

## Phase 3 — Project + Decision Memory（1.5 天）

### 目标
项目信息 + 关键决策持久化

### 新增
```
memory/types/project.py              ← ProjectMemory
memory/types/decision.py             ← DecisionMemory
memory/pipeline.py                   ← 扩展 close_session() (替代 app/pipeline.py)
```

### 数据库
```
CREATE TABLE project_memories (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    rules JSON DEFAULT '[]',
    decisions JSON DEFAULT '[]',
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)

CREATE TABLE decisions (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    session_id INTEGER,
    title TEXT NOT NULL,
    context TEXT DEFAULT '',
    options JSON DEFAULT '[]',
    chosen TEXT DEFAULT '',
    reason TEXT DEFAULT '',
    outcome TEXT DEFAULT '',
    created_at TIMESTAMP
)
```

### 修改
```
memory/pipeline.py close_session():
  扩展: 不只写 Conversation Memory
  → 提取 project_rules → ProjectMemory
  → 提取 decisions → DecisionMemory
```

### Phase 3 完成标准
- close_session() 自动提取 Project/Decision
- Context Engine 注入项目规则 → Layer 2/3
- 管理面板可查看/编辑 Project Memory

---

## Phase 4 — Ranking + Retriever 重构（1 天）

### 目标
从简单评分 → 多因子评分 + 独立 Retriever

### 新增
```
memory/retriever/__init__.py
memory/retriever/fts_retriever.py    ← FTSRetriever
memory/retriever/keyword_retriever.py ← KeywordRetriever
memory/ranking/__init__.py
memory/ranking/scorer.py             ← Scorer (多因子)
```

### 修改
```
memory/manager.py: query() 改造为:
  1. FTSRetriever.retrieve() → 0.40
  2. KeywordRetriever.retrieve() → 0.30
  3. Scorer.add_recency() → 0.15
  4. Scorer.add_importance() → 0.15
```

### Phase 4 完成标准
- 检索 + 评分完全解耦
- 新评分公式: 0.40*FTS + 0.30*Keyword + 0.15*Recency + 0.15*Importance
- 时间衰减生效 (30 天半衰期)

---

## Phase 5 — Knowledge Memory（1 天）

### 目标
长期知识库

### 新增
```
memory/types/knowledge.py            ← KnowledgeMemory
```

### 数据库
```
CREATE TABLE knowledge_entries (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_session_id INTEGER,
    tags JSON DEFAULT '[]',
    confidence FLOAT DEFAULT 0.5,
    expires_at TIMESTAMP,
    created_at TIMESTAMP
)
CREATE VIRTUAL TABLE knowledge_fts USING fts5(title, content, ...)
```

### Phase 5 完成标准
- 用户可手动添加知识
- close_session() 自动提取高置信知识
- 过期的自动标记 (不删除)

---

## Phase 6 — Cleanup + Archive（0.5 天）

### 目标
统一的淘汰和归档策略

### 新增
```
memory/cleanup/__init__.py
memory/cleanup/evictor.py            ← Evictor
memory/cleanup/scheduler.py          ← CleanupScheduler
```

### Phase 6 完成标准
- 所有 Memory 类型有独立 max_count
- 超量自动归档 JSONL
- 定时清理任务 (每天一次)

---

## Phase 7 — Vector Store（远期，2 天）

### 目标
语义搜索替代关键词搜索

### 新增
```
memory/embedding/embedder.py         ← Embedder
memory/storage/vector_store.py       ← VectorStore
memory/retriever/vector_retriever.py ← VectorRetriever
```

### Phase 7 完成标准
- 所有新 Memory 自动生成 embedding
- query() 增加 Vector 路 (三路召回: FTS + Keyword + Vector)
- 语义相似度搜索可用

---

## 工作量汇总

| Phase | 内容 | 天数 | 依赖 |
|-------|------|------|------|
| Phase 1 | 统一 Memory Schema | 1 天 | 无 |
| Phase 2 | User Memory | 1 天 | Phase 1 |
| Phase 3 | Project + Decision | 1.5 天 | Phase 1 |
| Phase 4 | Ranking + Retriever 重构 | 1 天 | Phase 1 |
| Phase 5 | Knowledge Memory | 1 天 | Phase 1 |
| Phase 6 | Cleanup + Archive | 0.5 天 | Phase 1 |
| Phase 7 | Vector Store | 2 天 (远期) | Phase 1-6 |
| **总计** | | **6 天 (不含 Vector)** | |

## 影响范围

| 文件 | Phase 1 | Phase 2-3 | Phase 4-6 |
|------|---------|-----------|-----------|
| memory.py | ❌ 删除 (被替代) | — | — |
| memory/ | ✨ 新建 10+ 文件 | ✨ 新建 5 文件 | ✨ 新建 5 文件 |
| pipeline.py | ✏️ 迁移到 memory/pipeline | ✏️ 扩展 | — |
| api.py | ✏️ 改用 MemoryManager | — | — |
| mother_runtime.py | ✏️ 改用 MemoryManager | — | — |
| models.py | 保持 (暂时) | — | 新增表 |
| schema/fts.sql | — | 新增 FTS 表 | 逐步替换 |

## 核心原则重复

```
Memory:  "过去发生了什么？" — 长期知识库 ← 本 Task
Context: "现在需要知道什么？" — 当前 Prompt 编排
Planner: "下一步做什么？"   — 任务分解
Runtime: "当前怎么执行？"   — Agent Loop

Memory 不侵入 Context Engine。
Context Engine 从 Memory 消费数据，但由 Context Engine 决定
取几条、放哪层、分配多少 Token。
```
