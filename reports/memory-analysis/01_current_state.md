# 任务一：当前 Memory 状态

## 数据层：5 表 + 2 FTS

```
sessions        ← 会话元数据 (状态/时间)
messages        ← 对话消息 (+ messages_fts FTS5 索引)
summaries       ← 会话摘要 (1:1 session)
keywords        ← 关键词 (1:N session, jieba 分词)
experiences     ← 经验记录 (+ experiences_fts FTS5 索引)
```

## 已存在

| Memory 类型 | 实现 | 表 | 级别 |
|------------|------|-----|------|
| Conversation Memory | session → summarize → write | summaries + keywords | ✅ 完整 |
| Experience Memory | LLM 提取 success/failure/lesson | experiences | ✅ 完整 |
| Session Memory | Session 表 (status/started_at/ended_at) | sessions | ✅ 基础 |
| Message History | Message 表 (role/content/created_at) | messages | ✅ 完整 |

## 缺失

| Memory 类型 | 说明 | 严重度 |
|------------|------|--------|
| **User Memory** | 用户画像/偏好/习惯 | 🔴 高 |
| **Project Memory** | 项目信息/规则/上下文 | 🔴 高 |
| **Decision Memory** | 关键决策记录（为什么选这个方案） | 🟡 中 |
| **Knowledge Memory** | 长期知识库（非对话总结） | 🟡 中 |
| **Capability Memory** | 工具使用经验（哪个工具好用） | 🟢 低 |
| **Observation Memory** | 环境观察记录（设备状态变化） | 🟢 低 |
| **Evolution Memory** | 自我进化记录（配置变更/Bug修复） | 🟢 低 |
| **Vector Store** | 向量嵌入 + 语义搜索 | 🔴 高 |
| **Embedding** | 文本 → 向量 | 🔴 高 |

## 重复

无显著重复。各表职责清晰。

## 检索方式

```
query(q, top_n=3):
  A. FTS5 搜索 messages_fts  → score = 0.6 * (fts_score / fts_max)
  B. jieba 分词 → keywords 表匹配 → score += 0.4 * (match_count / match_max)
  合并去重 → 按 score 降序 → top_n
```

## 当前生命周期

```
Session active → 消息写入 messages → Session close:
  1. pipeline.close_session():
     LLM.summarize_session() → summary + keywords + experiences
  2. MemoryRepo.write_session_memory() → summaries + keywords + experiences
  3. FTS5 trigger 自动更新索引
召回:
  MotherRuntime.run() → MemoryRepo.query(msg, 3) → WorkingMemory.set_recall()
淘汰:
  experiences > 1000 → 归档到 JSONL → 删除旧记录
```
