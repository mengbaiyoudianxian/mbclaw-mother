# 任务七：Memory 完整生命周期

## 写流程（Session Close）

```
[1] Session Active
    Runtime 处理用户消息 → messages 写入 DB → FTS5 trigger 自动索引
    │
    ▼
[2] Session Close Trigger
    用户主动关闭 / 超时 / 新建 Session 时触发
    入口: api.py POST /sessions/{id}/close
    │
    ▼
[3] Load Messages
    从 messages 表加载本 session 全部消息
    → [Message {role, content, created_at}, ...]
    │
    ▼
[4] LLM Summarize
    LLMClient.summarize_session(messages) → LLMOutput
    输出:
      summary: ≤300 字会话摘要
      keywords: ≤10 个关键词
      experiences: ≤5 条 (success/failure/lesson)
    │
    ▼
[5] jieba TF-IDF
    全文关键词提取 (jieba.analyse.extract_tags)
    与 LLM 关键词合并: LLM_weight=1.0, jieba_weight=0.5
    → top 10 合并关键词
    │
    ▼
[6] Write Conversation Memory
    写入:
      summaries: session_id → summary (覆写)
      keywords:  session_id → [keyword, weight] (覆写)
    │
    ▼
[7] Write Experience Memory
    写入:
      experiences: session_id → [kind, title, content]
    FTS5 trigger 自动索引到 experiences_fts
    │
    ▼
[8] Extract Other Memories (远期)
    LLM 提取:
      decisions: "用户选择了方案A → 因为兼容性更好" → DecisionMemory
      knowledge: "Python 3.12 的 match-case 语法" → KnowledgeMemory
      project:   "用户偏好 WebSocket 通信" → ProjectMemory rule
    │
    ▼
[9] Mark Session Closed
    session.status = "closed"
    session.ended_at = now()
    │
    ▼
[10] Eviction Check
    if experience_count > 1000:
      归档最旧的 (total - 1000) 条 → JSONL
    (远期: 所有 Memory 类型都有淘汰策略)
```

## 读流程（Context Recall）

```
[1] Context Engine 发起请求
    ContextEngine.build() → MemoryManager.query(msg, top_n=3)
    │
    ▼
[2] Tokenize
    jieba.cut_for_search(msg) → tokens
    │
    ▼
[3] Dual Retrieve
    ├── A. FTS5 搜索:
    │   messages_fts MATCH query → [(session_id, summary, rank)]
    │   score_a = 0.40 * (rank / max_rank)
    │
    └── B. Keyword 搜索:
        keywords 表 IN (tokens) → [(session_id, summary, keyword)]
        score_b = 0.30 * (match_count / max_match)
    │
    ▼
[4] Merge + Dedup
    按 session_id 合并 A + B
    score = score_a + score_b
    │
    ▼
[5] Recency Bonus (当前缺失)
    按会话结束时间衰减:
    recency = 0.15 * exp(-days_since_close / 30)
    score += recency
    │
    ▼
[6] Importance Bonus
    by kind priority:
    failure > lesson > success
    importance = 0.15 * priority_weight
    score += importance
    │
    ▼
[7] Sort + Top-N
    按 final_score 降序 → top_n=3
    │
    ▼
[8] Return to Context Engine
    [MemoryHit {session_id, summary, keywords, score, source}]
    → Context Engine 决定如何注入 Prompt
    │
    ▼
[9] Update Recall Count (Experience only)
    对返回的 experiences: recall_count++ (影响后续排序)
```

## 更新流程

```
[1] Session 持续对话
    messages 表持续追加 → FTS5 trigger 实时索引
    ────── 不更新 summaries/keywords/experiences ──────
    (只在 Session close 时写入一次)

[2] User Profile 更新
    对话中检测到:
      - 用户提了新偏好 → upsert user_preferences
      - 用户换了设备 → 追加 devices
      - 用户名/身份变更 → update user_profile
    触发: Runtime 检测 → MemoryManager.update("user", data)
    ────── 实时更新 ──────

[3] Project Memory 更新
    对话中 LLM 识别到:
      - 新增项目规则 → append project.rules
      - 关键决策 → insert decisions
    ────── 实时更新 (通过 MemoryManager) ──────
```

## 淘汰流程

```
[1] Eviction Trigger
    定时 (每天) 或 写入时检查:
    ├── experiences > 1000 → archive
    ├── observations > 5000 → archive (30天前的)
    └── knowledge (expires_at 到期) → 标记 expired
    │
    ▼
[2] Select Candidates
    ORDER BY created_at ASC → LIMIT (total - max_count)
    │
    ▼
[3] Archive to JSONL
    写入 data/archive/{type}-{year-month}.jsonl
    │
    ▼
[4] Delete from DB
    DELETE FROM {table} WHERE id IN (candidates)
    │
    ▼
[5] Rebuild FTS (if needed)
    FTS5 content table 在 DELETE trigger 自动更新 ✅
    不需要手动重建
```

## 完整状态机

```
                   ┌──────────────────┐
                   │  Session Active   │
                   │  messages 实时写入 │
                   └────────┬─────────┘
                            │ close_session()
                            ▼
                   ┌──────────────────┐
                   │  LLM Summarize    │
                   │  summary+keywords │
                   │  +experiences     │
                   └────────┬─────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        summaries     keywords     experiences
        (覆写)        (覆写)        (追加)
              │             │             │
              └─────────────┼─────────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │  Mark Closed      │
                   │  status=closed    │
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │ Eviction Check    │
                   │ >1000 → archive   │
                   └──────────────────┘
```
