## ADR-003: SQLite+FTS5 保留

Status: Accepted (2026-07-09)

### 决策
保留 SQLite+FTS5+jieba 作为长期记忆存储。当前规模无需外部向量数据库。

### 触发迁移条件
单表>1000万消息 或 需要向量语义检索 或 需要分布式。
