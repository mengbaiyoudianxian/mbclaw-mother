# 任务二：Claude Code Context 管理

## 核心分析

Claude Code Context 管理是行业标杆。以下分析来自官方文档和插件源码。

---

## Claude Code Context 设计

### 分层 Prompt 结构

```
System Prompt (Claude Code)
├── Layer 1: Base Identity      "你是一个 AI 编程助手..."
├── Layer 2: Tool Definitions   已注册工具列表 (JSON Schema)
├── Layer 3: Rules              CLAUDE.md + project rules
├── Layer 4: Active Context     当前文件 + 光标位置
├── Layer 5: Memory             项目级记忆 (CLAUDE.md MEMORY section)
├── Layer 6: Conversation       最近对话 (自动压缩)
└── Layer 7: User Message       当前用户输入
```

### 重要性压缩（核心能力）

```
Claude Code 压缩策略:
  保留 (保留在上下文中):
    ✅ 关键决策 (用户确认的方向)
    ✅ 文件修改摘要 (改了哪个文件、为什么)
    ✅ TODO 状态 (pending/in_progress/done)
    ✅ 当前问题 (未解决的错误)

  丢弃 (从上下文中移除):
    ❌ 中间工具输出 (已处理完毕的结果)
    ❌ 已解决的错误堆栈
    ❌ 冗余的重复信息
    ❌ 低信息量的确认消息

  触发:
    自动: token 接近模型上限时
    手动: 用户执行 /compact 命令
```

### Checkpoint + Context Restore

```
Claude Code Checkpoint:
  每轮工具执行前:
    save_checkpoint()
      ├── file_snapshot: {path: content_hash}  ← 文件状态
      ├── context_snapshot: messages_at_checkpoint  ← 对话状态
      └── metadata: {turn, tool, timestamp}

  用户拒绝 / 错误:
    rollback()
      ├── restore files  (git checkout)
      ├── restore context (消息恢复到 checkpoint 时)
      └── 重新开始 or abort
```

### Long Context 管理

```
Claude Code 长会话策略:
  1. 内部自动压缩 (重要性算法)
  2. 关键信息提取 → 保存到 CLAUDE.md MEMORY
  3. 下一个会话加载 CLAUDE.md → 恢复关键上下文
  4. TodoWrite 工具: LLM 输出结构化 TODO 跨轮保持
```

---

## 值得借鉴的设计

| Claude 设计 | MBclaw Context Engine | 优先级 |
|------------|----------------------|--------|
| **分层 Prompt** | Layer 1-7 独立构建 → ContextEngine.build_prompt() | P0 |
| **重要性压缩** | 按信息量评分保留 → Compressor.compress() | P0 |
| **Context Restore** | Checkpoint 恢复 → ContextEngine.restore(checkpoint_id) | P1 |
| **关键决策保留** | 压缩时保留决策节点 → Compressor 保留策略 | P1 |
| **TodoWrite 跨轮** | TODO 不参与压缩 → Compressor 跳过 TODO | P2 |
| **Token Budget** | 按层分配预算 → BudgetManager.allocate() | P1 |

## 不能借鉴的

| Claude 设计 | 原因 |
|------------|------|
| /compact 命令 | MBclaw 无需手动触发，自动压缩 |
| Git 文件快照 | MBclaw 是对话场景，不需要文件回退 |
| CLAUDE.md | MBclaw 用户没有项目级规则文件 |
| 光标/文件上下文 | MBclaw 是个人助理，不是 IDE 编程助手 |

## 推荐指数

★★★★★ — 重要性压缩 + 分层 Prompt 是 Context Engine 核心设计
