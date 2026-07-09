# 任务三：Claude Code Memory

## Claude Code 记忆机制

### Project Memory (CLAUDE.md)

```
CLAUDE.md:
  # Project Overview
  ## Architecture
  ## Memory (关键！)
    - 上次报错原因: xxx
    - 用户偏好: 用 async/await 不用回调
    - 关键决策: 选中方案A 因为兼容性
  ## Rules

Claude 启动时加载 CLAUDE.md → 注入 System Prompt
关闭时: 将关键信息写回 CLAUDE.md MEMORY section
```

### Long-Term Memory 策略

```
避免 Context 无限增长:
  1. 压缩: 重要性评分 → 丢弃低信息内容
  2. 持久化: 关键信息写入 CLAUDE.md
  3. 恢复: 下次启动从 CLAUDE.md 加载
  4. 工具化: TodoWrite 保持 TODO 跨轮
```

### Conversation Summary

```
Session 关闭时:
  Claude Code 生成自然语言摘要:
    "用户要求添加 JWT 认证。实现了 login/logout 端点，
     使用 HS256 算法。遇到 token 过期问题，
     通过配置 exp claim 解决。未完成: refresh token。"
  写入 CLAUDE.md MEMORY section
  下次对话: 摘要作为上下文注入
```

### Context Restore

```
新对话启动:
  1. 加载 CLAUDE.md → 项目规则 + 历史摘要
  2. 加载 .claude/settings.json → 用户偏好
  3. 注入 System Prompt
  → 新对话自动继承上次上下文
```

---

## 可直接借鉴

| Claude 设计 | MBclaw Memory | 优先级 |
|------------|-------------|--------|
| **CLAUDE.md MEMORY** | User/Project Memory 表 | P0 |
| **关闭时写摘要** | 已有 pipeline.close_session() ✅ | 已实现 |
| **启动时恢复** | render_injection_for_new_session() ✅ | 已实现 |
| **关键决策持久化** | Decision Memory 表 | P1 |
| **用户偏好存储** | User Memory (user_preferences) | P1 |
| **TodoWrite 跨轮** | Planner 管理 (非 Memory) | P2 |

## 不能直接翻译的

| Claude 设计 | 原因 |
|------------|------|
| CLAUDE.md 文件格式 | MBclaw 没有项目级文件系统，用 DB 表 |
| .claude/settings.json | MBclaw 用户设置存 DB |
| /compact 命令 | MBclaw 自动压缩 |

## 推荐指数

★★★★★ — CLAUDE.md MEMORY 模式 (关闭写摘要 → 启动恢复) 是 Memory 核心设计
