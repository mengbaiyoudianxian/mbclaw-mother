# 任务七：Context Engine 完整生命周期

```
[1] Receive message
    Runtime 收到用户消息
    输入: Message {role, content, user_id, channel}
    触发: 每个用户消息
    │
    ▼
[2] Load Session
    从 SessionStore 获取/创建 Session
    输入: session_id
    输出: Session {history, state, metadata}
    状态: session_loading
    │
    ▼
[3] Load Memory
    从 Memory 模块搜索相关记忆
    输入: user_message, top_n=3
    输出: [MemoryHit {summary, keywords, session_id}]
    数据源: Memory.query()
    Context Engine 决定: 取前 3 条
    │
    ▼
[4] Load History
    从 Session 提取对话历史
    输入: Session.history
    输出: [Message {role, content, ts}]
    规则: 取最近消息 (具体条数取决于 Budget)
    │
    ▼
[5] Estimate Token Budget
    计算当前预算:
    ├── 模型 token_limit (例如: gpt-4o-mini = 128k, 实际用 6k 预算)
    ├── 各层分配比例:
    │   Layer 1 (Identity):   5% →  300 tokens
    │   Layer 2 (Governor):   5% →  300 tokens
    │   Layer 3 (Memory):    15% →  900 tokens
    │   Layer 4 (Planner):   10% →  600 tokens
    │   Layer 5 (Tools):     25% → 1500 tokens
    │   Layer 6 (History):   40% → 2400 tokens
    │   Layer 7 (Active):     5% →  300 tokens
    │   Layer 8 (User):       5% →  300 tokens
    └── 总计: 6000 tokens
    状态: budget_estimating
    │
    ▼
[6] Check History Overflow
    判断: Layer 6 History 是否超预算？
    ├── 未超 → 跳过压缩 [8]
    └── 已超 (60% threshold) → 需要压缩 [7]
    状态: overflow_checking
    │
    ▼
[7] Compress
    Compressor 执行压缩:
    a. 重要性评分 (scorer.py):
       每条消息评分 0-10
       P0 (10分): 用户指令 → 永久保留
       P1 (8分):  关键决策 → 保留
       P2 (6分):  工具结果 → 保留摘要
       P3 (5分):  当前错误 → 保留
       P4 (2分):  已解决错误 → 丢弃
       P5 (0分):  低信息消息 → 丢弃
    b. 保留 P0-P3 的消息
    c. 丢弃的消息 → LLM 生成语义摘要
    d. 替换: [摘要] + [P0-P3 保留消息]
    状态: compressing
    可自动: ✅ 是
    │
    ▼
[8] Build Context
    PromptPipeline 按层序构建:
    Layer 1: 加载 identity.yml → 插入 content
    Layer 2: Governor.get_policy() → 插入权限约束
    Layer 3: Memory hits → 格式化为"相关记忆：..."
    Layer 4: Planner.get_status() → 插入 Task 状态
    Layer 5: CapabilityRegistry.list() → 生成工具列表
    Layer 6: History (压缩后) → 插入对话历史
    Layer 7: 当前工具结果/错误 → 插入
    Layer 8: 用户输入 → 插入
    状态: building
    │
    ▼
[9] Send to LLM
    将构建好的 messages 传给 Scheduler
    输出: [{"role":"system","content":...}, {"role":"user","content":...}]
    状态: dispatching
    阻塞: 等待 LLM 响应
    │
    ▼
[10] Receive Reply
    LLM 返回响应
    ├── text → 最终回复 → [11] Save History
    └── tool_call → 执行工具 → 结果追加 → [5] Estimate Budget → 下一轮
    状态: receiving
    │
    ▼
[11] Save History
    将本轮消息写入 Session:
    ├── User Message → Session.add()
    ├── Assistant Reply → Session.add()
    └── Tool Result → Session.add()
    更新 Memory: 可选 (Memory 模块负责)
    状态: saving
    │
    ▼
[12] Checkpoint (可选)
    if Governor 决定需要 Checkpoint:
      ContextCheckpoint.save(
        messages=当前上下文,
        budget_state=当前预算,
        compressor_state=压缩器状态
      )
    状态: checkpointing
    │
    ▼
[13] Complete
    返回最终回复给 Runtime
    状态: completed
    清理: 不清理 (Context Engine 保持 Session 状态)
```

## 状态机

```
receiving → session_loading → memory_loading → history_loading
                                                   │
                                                   ▼
                                            budget_estimating
                                                   │
                                        ┌──────────┴──────────┐
                                        ▼                     ▼
                                   overflow_check       no_overflow
                                        │                     │
                                        ▼                     │
                                    compressing              │
                                        │                     │
                                        └──────────┬──────────┘
                                                   ▼
                                               building
                                                   │
                                                   ▼
                                              dispatching
                                                   │
                                        ┌──────────┴──────────┐
                                        ▼                     ▼
                                    receiving             tool_call
                                   (final reply)             │
                                        │              ┌─────┘
                                        ▼              ▼
                                    saving     budget_estimating
                                        │         (下一轮)
                                        ▼
                                    checkpointing
                                   (optional)
                                        │
                                        ▼
                                    completed
```

## 关键决策点

| 决策 | 触发条件 | 选项 |
|------|---------|------|
| 是否压缩 | History > 60% budget | compress / skip |
| 保留什么 | 压缩时每条评分 | P0-P3 keep / P4-P5 drop |
| LLM 摘要还是简单拼接 | 压缩时 | LLM 生成语义摘要 (优先) / 简单拼接 (fallback) |
| Memory 条目 | 搜索结果 | top_n=3 (当前) / top_n=5 (长会话) |
| Budget 分配 | 模型不同 | gpt-4o-mini=6000 / claude=8000 / 本地=16000 |
| Checkpoint | 每轮 / 关键操作前 | save / skip |
