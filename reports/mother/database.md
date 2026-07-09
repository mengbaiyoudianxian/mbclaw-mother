# Mother Database 分析

## 作用

数据库层提供持久化存储，使用 SQLite + WAL 模式 + FTS5 全文索引。

## 当前实现

文件：`app/db.py`（61 行）、`app/models.py`（112 行）、`app/schema/fts.sql`（55 行）

### 引擎配置
- **数据库**：SQLite，路径由 `MBCLAW_DB_PATH` 环境变量指定（默认 `data/mbclaw.db`）
- **WAL 模式**：PRAGMA journal_mode=WAL
- **同步级别**：PRAGMA synchronous=NORMAL
- **缓存**：PRAGMA cache_size=-20000（20MB）
- **临时存储**：PRAGMA temp_store=MEMORY
- **连接**：check_same_thread=False（FastAPI 多线程）

### 数据模型（7 张表）

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| sessions | 会话记录 | id, title, status, context, started_at, ended_at |
| messages | 消息记录 | id, session_id(FK), role, content, created_at |
| summaries | 会话摘要 | id, session_id(UNIQUE FK), summary |
| keywords | 关键词 | id, session_id(FK), keyword, weight |
| experiences | 经验沉淀 | id, session_id(FK), kind, title, content, recall_count |
| tools | 工具注册表 | id, name(UNIQUE), category, tags, parameters, usage_count |
| model_profiles | LLM Provider 配置 | id, key_alias(UNIQUE), provider, model_name, api_base, priority |

### FTS5 虚拟表
- `messages_fts`：对 messages.content 做全文索引
- `experiences_fts`：对 experiences.title + content 做全文索引
- 6 个触发器保持 FTS 与主表同步（INSERT/DELETE/UPDATE 各一）

### Session 管理
- `SessionLocal` = sessionmaker（FastAPI Depends 方式注入）
- `get_db()` 作为 FastAPI 依赖，自动 close
- 无连接池（SQLite 单文件）

## 存在问题

1. **SQLite 不适合高并发**：单文件写入瓶颈，虽然 WAL 模式有改善
2. **无迁移工具**：`Base.metadata.create_all()` 只能建表，无法处理 schema 变更
3. **FTS5 tokenizer 为 unicode61**：不支持中文分词，中文检索效果差
4. **没有全文搜索的 ranking 调优**：使用默认 BM25，未针对中文优化
5. **admin 数据使用独立 JSON 文件**：admin.json、users.json、stats.json、keys.json 与 SQLite 并行，数据分散
6. **心跳数据使用独立 JSON 文件**：heartbeat_logs/*.json，不在 SQLite 中
7. **没有索引优化**：messages.session_id 等高频查询字段未见显式索引（SQLAlchemy ForeignKey 自动建索引）

## 建议

1. 短期：SQLite 可保留，但需引入 Alembic 做 schema 迁移
2. 中期：考虑将 admin JSON 数据迁移到 SQLite
3. 长期：如需高并发，考虑迁移到 PostgreSQL
4. 中文分词：考虑编译 jieba tokenizer 或迁移到外部检索引擎
5. 增加常用查询索引

## 以后是否保留

**保留**。SQLite + WAL 模式对于当前规模足够。但需要：
- 引入 Alembic 做 schema 迁移
- 统一 admin JSON 数据到 SQLite
- 评估中文检索方案
