# Mother Memory 分析

## 作用

Memory 模块是母体的长期记忆系统，负责对话摘要、关键词提取、经验沉淀和双路召回检索。

主要职责：
- write_session_memory：原子写入摘要 + 关键词 + 经验
- query：双路召回（FTS5 全文检索 + jieba 关键词匹配）
- query_experiences：经验检索（含 kind-priority + recency bonus）
- render_injection_for_new_session：新会话自动注入上次关键事实和教训
- _maybe_evict_experiences：经验超 1000 条时自动归档

## 当前实现

文件：`app/memory.py`，约 193 行。

### 数据模型（models.py）
5 张核心表：
- `sessions`：会话（id, title, status, context, started_at, ended_at）
- `messages`：消息（session_id, role, content, created_at）
- `summaries`：摘要（session_id UNIQUE, summary）
- `keywords`：关键词（session_id, keyword, weight）
- `experiences`：经验（session_id, kind, title, content, keywords_json, recall_count）

### FTS5 索引（schema/fts.sql）
- `messages_fts`：对 messages.content 做全文索引（unicode61 tokenizer）
- `experiences_fts`：对 experiences.title + content 做全文索引
- 6 个触发器保持 FTS 索引与主表同步

### 双路召回算法
- **FTS 路**（权重 0.6）：SQLite FTS5 MATCH 查询 messages_fts
- **关键词路**（权重 0.4）：jieba 分词后匹配 keywords 表
- 两条路的得分加权求和后排序，取 top_n

### 经验检索
- FTS5 搜索 + kind-priority（failure=1.0 > lesson=0.8 > success=0.5）
- recency bonus = log(recall_count + 1)
- 检索后自动更新 recall_count

### 归档策略
- 经验数 > 1000 时，最旧的被写入 `data/archive/experiences-YYYY-MM.jsonl`
- 从数据库删除已归档经验

## 存在问题

1. **FTS5 tokenizer 为 unicode61**：对中文分词效果差，实际主要依赖 jieba 关键词路
2. **双路召回评分公式粗糙**：FTS 的 rank 直接取绝对值，归一化方式简单
3. **经验检索的 FTS 和 bonus 权重（0.7 : 0.3）为固定值**，未经过调优
4. **归档文件为 JSONL**：只追加不压缩，长期会产生大文件
5. **没有 embedding 向量检索**：纯关键词匹配，无法做语义搜索
6. **MemoryRepo 强依赖 SQLAlchemy Session**：无法独立测试
7. **render_injection_for_new_session 查询效率低**：需多次查询+二次检索

## 建议

1. 考虑引入 jieba 分词器替换 unicode61（需编译自定义 tokenizer）或迁移到支持中文的检索引擎
2. 增加 embedding 向量检索作为第三路召回
3. 归档文件增加定期压缩合并逻辑
4. 评分权重可配置化

## 以后是否保留

**保留核心设计，数据库层可保留**。双路召回思路正确，但需要升级到支持中文分词和向量检索。数据模型设计合理，5 表结构清晰。
