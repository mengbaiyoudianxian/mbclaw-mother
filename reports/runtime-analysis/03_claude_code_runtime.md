# 任务三：Claude Code Runtime 分析

## 核心发现

Claude Code 核心闭源。公开内容仅为插件市场。以下分析基于官方文档 code.claude.com。

## Claude Code Runtime 设计（从文档还原）

```
用户输入 → System Prompt (tools+rules+memory+skills)
         → Claude API (streaming)
         → 边接收边解析: thinking <-> tool_use 交替
         → 执行工具 → 结果追加
         → 循环 (最多 N 轮)
         → 最终回复
```

## Claude Code 独有的 5 个 Runtime 设计

### 1. 智能上下文压缩（行业标杆）

```
Claude: 保留关键决策/文件修改摘要/TODO → 丢弃中间工具输出/已解决错误
MBclaw: 保留后一半 + 前一半拼接 → 丢弃前一半详细内容
```

### 2. Checkpoint

```
Claude: 每轮工具执行前创建文件快照 → 失败回退文件+对话状态
MBclaw: 无 Checkpoint → 失败返回错误文本，用户重来
```

### 3. Streaming Agent Loop

```
Claude: LLM输出streaming → 边接收边解析 → tool_use不需要等完整响应
MBclaw: 等待完整HTTP响应 → 然后解析 → 用户等待=完整LLM响应时间
```

### 4. Plugin System

```
Claude: .claude-plugin/marketplace.json → hooks+commands+custom agents
MBclaw: 无插件系统 (Capability Registry 规划中)
```

### 5. Prompt Runtime（分层）

```
Claude: base(CLI用途) + .claude/settings.json + CLAUDE.md + 目录上下文 + 工具列表
MBclaw: 一个硬编码 AGENT_PROMPT + TOOL_DEFS_TEXT
```

## 值得借鉴

| 设计 | 借鉴方式 | 优先级 |
|------|---------|--------|
| 智能压缩 | ContextEngine 重要性评分 | P0 |
| Checkpoint | Governor checkpoint() | P1 |
| Streaming Loop | Scheduler + stream | P2 |
| 分层 Prompt | Prompt Builder | P1 |
| Plugin 注册 | Capability Registry | P1 |

## 不能迁移

- Claude API 专有 (thinking <-> tool_use 交替) — 仅 Claude 模型支持
- 文件 Checkpoint — MBclaw 是对话场景，不需要文件快照
- /compact 命令 — MBclaw 自动触发即可

## 推荐指数

★★★★☆ — 压缩 + Checkpoint 设计最有价值
