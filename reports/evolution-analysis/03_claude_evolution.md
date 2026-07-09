# 任务三：Claude Code Evolution

## Claude Code 自我改进机制

### 用户纠正 → 行为改变

```
Claude Code 纠正流程:
  1. 用户: "不对，你应该用 async 而不是回调"
  2. Claude: 识别纠正 → 提取规则
  3. 写入 CLAUDE.md MEMORY:
     ## Memory
     - 用户偏好: 使用 async/await，不用回调
  4. 下次对话: 从 CLAUDE.md 加载 → 使用 async

归入: Memory (用户偏好)
不是: Evolution (没有改变系统行为，只是记住了偏好)
```

### 项目规则 → 工作流改进

```
Claude Code 规则学习:
  1. 用户: "所有 PR 必须通过 CI 检查才能合并"
  2. Claude: 提取规则 → 写入 CLAUDE.md Rules
  3. 以后: 每次创建 PR 前自动检查 CI

归入: Memory (项目规则)
```

### 哪些属于 Memory，哪些属于 Evolution

| Claude Code 行为 | 归属 | 原因 |
|-----------------|------|------|
| 记住用户偏好 (async/await) | Memory | 保存信息 |
| 记住项目规则 (CI 检查) | Memory | 保存规则 |
| 从错误中改进工具调用 | Evolution | 改变行为策略 |
| 自动优化 Workflow (多步骤合并) | Evolution | 改变执行方式 |
| 自动调整 Tool 参数 (timeout 增加) | Evolution | 改变系统参数 |

---

## 可借鉴的设计

| Claude 设计 | MBclaw Evolution | 优先级 |
|------------|-----------------|--------|
| **用户纠正 → 规则提取** | Evolution 分析纠正模式 → 建议规则 | P1 |
| **CLAUDE.md MEMORY 更新** | Memory 更新 (但 Evolution 提议) | P1 |
| **Workflow 优化** | Evolution 分析多轮 → 建议合并步骤 | P2 |
| **Tool 参数自动调整** | Evolution 分析超时 → 建议增加 timeout | P2 |

## 推荐指数

★★★☆☆ — 用户纠正 → 规则提取可借鉴，但 Claude 没有真正的 Evolution Engine
