# 任务五：最终 Memory 设计

## 核心定位

```
Memory:  "过去发生了什么？"  — 长期知识库
Context: "现在需要知道什么？" — 当前 Prompt 编排
Planner: "下一步做什么？"    — 任务分解
Runtime: "当前怎么执行？"    — Agent Loop
```

---

## Memory 九层记忆体系

### Layer 1: Conversation Memory（会话记忆）✅ 已有

```
存储: Session 关闭时 → LLM 摘要 → summaries 表
内容: 会话摘要 + 关键词
检索: FTS5 + jieba dual-recall
生成: pipeline.close_session()
调用: Context Engine (Layer 3: Memory Recall)
生命周期: Session close → write → 不淘汰 (永久保留)
```

### Layer 2: Project Memory（项目记忆）❌ 缺失

```
存储: project_memories 表
内容: 项目名称/描述/规则/关键决策/状态
检索: 项目 ID 精确查询
生成: 用户定义 + 自动提取 (从对话)
调用: Context Engine (Layer 3 或 Layer 2 Governor)
生命周期: 手动创建 → 对话自动更新 → 手动删除
表: id, name, description, rules, decisions (JSON), created_at, updated_at
```

### Layer 3: Decision Memory（决策记忆）❌ 缺失

```
存储: decisions 表
内容: 决策描述/上下文/选项/选择理由/结果
检索: FTS5 + 时间衰减
生成: 对话中识别决策点 → LLM 提取
调用: Context Engine (预防重复错误)
生命周期: 对话中提取 → 关联 project → 永久保留
表: id, project_id, session_id, title, context, options (JSON), chosen, reason, outcome, created_at
```

### Layer 4: Experience Memory（经验记忆）✅ 已有

```
存储: experiences 表 (+ experiences_fts)
内容: kind (success/failure/lesson) + title + content
检索: FTS5 + kind-priority + recency bonus ✅
生成: pipeline.close_session() → LLM summarise ✅
调用: render_injection_for_new_session() ✅
生命周期: Session close → write → >1000 → JSONL 归档 ✅
```

### Layer 5: Knowledge Memory（知识记忆）❌ 缺失

```
存储: knowledge_entries 表 + knowledge_fts
内容: 标题/内容/来源/标签/置信度
检索: FTS5 + 向量语义搜索 (未来)
生成: 用户手动添加 + 自动从对话提取长时效信息
调用: Context Engine (Layer 3)
生命周期: 手动/自动创建 → 时效检查 → 过期标记 (非删除)
表: id, title, content, source_session_id, tags (JSON), confidence, expires_at, created_at
```

### Layer 6: User Memory（用户记忆）❌ 缺失

```
存储: user_profiles 表
内容: user_id/偏好/习惯/设备列表/常用命令/语言/时区
检索: user_id 精确查询
生成: 从对话中自动提取 + 用户显式设置
调用: Context Engine (Layer 2 Governor 或 Layer 3)
生命周期: 创建 → 持续更新 → 删除 (用户注销)
表: id, user_id, preferences (JSON), habits (JSON), devices (JSON), stats (JSON), updated_at
```

### Layer 7: Capability Memory（能力记忆）❌ 缺失

```
存储: 可扩展 tools 表 (已有 tool usage_count) + capability_usage 表
内容: 工具使用频率/成功率/平均延迟/最佳参数
检索: tool.name 精确查询
生成: Scheduler 每次执行后写入
调用: Scheduler/CapabilityRegistry (优化工具推荐)
生命周期: 实时更新 → 定期聚合 → 短期保留 (30天)
表: id, tool_name, success_count, error_count, avg_latency, last_used, best_params (JSON)
```

### Layer 8: Observation Memory（观察记忆）❌ 缺失

```
存储: observations 表
内容: 设备状态变化/系统事件/错误日志摘要
检索: 时间范围 + FTS5
生成: 设备心跳变化时自动记录
调用: Governor (风险检测) + Context Engine (环境上下文)
生命周期: 事件触发 → 写入 → 30 天过期
表: id, event_type, device_code, before_state, after_state, timestamp
```

### Layer 9: Evolution Memory（进化记忆）❌ 缺失

```
存储: evolutions 表
内容: 配置变更/代码更新/Bug修复/性能优化记录
检索: 时间序
生成: 每次自我更新时记录
调用: Governor (安全审计) + 管理面板
生命周期: 变更触发 → 写入 → 永久保留 (审计)
表: id, change_type, description, before_snapshot, after_snapshot, reason, created_at
```

---

## Memory vs Context Engine 边界（铁律）

```
Memory (存储层):
  ✅ 存储: summaries / experiences / knowledge / user profiles / decisions
  ✅ 检索: query(msg, top_n) → [MemoryHit]
  ✅ 写入: write_*()
  ✅ 淘汰: evict/archive
  ❌ 不决定: 取几条、放 Prompt 哪层、分配多少 Token

Context Engine (编排层):
  ✅ 决定: Memory 召回几条 → top_n=3
  ✅ 决定: 放 Prompt Layer 3 (Memory Recall)
  ✅ 决定: 分配 15% Token Budget (900 tokens)
  ✅ 截断: 每条 summary 最多 300 tokens
  ❌ 不存储: 任何 Memory 数据
  ❌ 不检索: 委托 Memory.query()
```

## 各层优先级

| Layer | 当前状态 | 优先级 | Phase |
|-------|---------|--------|-------|
| 1 Conversation | ✅ 完整 | — | — |
| 4 Experience | ✅ 完整 | — | — |
| 2 Project | ❌ 缺失 | P1 | Phase 3 |
| 6 User | ❌ 缺失 | P1 | Phase 2 |
| 3 Decision | ❌ 缺失 | P2 | Phase 4 |
| 5 Knowledge | ❌ 缺失 | P2 | Phase 5 |
| 7 Capability | ❌ 缺失 | P3 | Phase 6 |
| 8 Observation | ❌ 缺失 | P3 | 远期 |
| 9 Evolution | ❌ 缺失 | P3 | 远期 |
