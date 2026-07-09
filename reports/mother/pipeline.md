# Mother Pipeline 分析

## 作用

Pipeline 模块实现会话关闭流程：加载消息 → LLM 摘要 → jieba 关键词提取 → 记忆持久化 → 标记关闭。

## 当前实现

文件：`app/pipeline.py`，75 行。

### close_session() 流程

```
输入：db session, session_id, LLMClient
    ↓
1. 检查 session 是否存在
    ↓
2. 幂等检查：如果已关闭，返回缓存结果
    ↓
3. 加载全部消息（db.query(Message)）
    ↓
4. LLM 摘要：llm.summarize_session(msg_dicts)
   → 返回 LLMOutput {summary, keywords, experiences}
    ↓
5. jieba TF-IDF 关键词提取（topK=10）
   → 与 LLM 关键词合并（LLM:1.0, jieba:0.5*weight）
    ↓
6. MemoryRepo.write_session_memory(sid, summary, merged_kws, exp_dicts)
    ↓
7. 更新 session.status = "closed"
    ↓
输出：{session_id, status, summary, keywords, experiences, stats}
```

### 关键词合并策略
- LLM 提取的关键词权重 = 1.0（信任度高）
- jieba TF-IDF 权重 = 0.5 × TF-IDF weight
- 重复关键词权重叠加
- 最终取 top 10

## 存在问题

1. **功能单一**：只有 close_session 一个函数，且只在 `/sessions/{sid}/close` 端点被调用
2. **关键词合并权重硬编码**：LLM=1.0, jieba=0.5 无调优依据
3. **全量加载消息**：长会话可能导致内存压力（无分页/截断）
4. **无异步处理**：整个流程是同步的，阻塞 HTTP 请求
5. **与 agent.py 功能重叠**：agent_run 也会写 Message、调 MemoryRepo，但走不同路径
6. **关闭后无后续处理**：无 post-close hook（通知、告警等）

## 建议

1. 可考虑将 close_session 改为后台任务（FastAPI BackgroundTasks）
2. 长会话消息应分批处理或截断
3. 增加关闭后回调机制

## 以后是否保留

**保留**。功能清晰、单一职责。但需要：
- 改为异步/后台执行
- 增加消息分批处理
- 关键词权重可配置化
