# 任务一：当前 Evolution 状态

## 结论：Evolution 不存在

MBclaw 当前没有任何 Evolution 系统。唯一的间接关联是 Memory 中的 Experience 记录。

---

## 已存在（但属于 Memory，不属于 Evolution）

| 能力 | 实现 | 位置 | 归属 |
|------|------|------|------|
| Success/Failure/Lesson 记录 | LLM summarise → experiences 表 | memory.py + pipeline.py | Memory ✅ |
| 上次失败召回 | render_injection_for_new_session() | memory.py L147-154 | Context Engine ✅ |
| 经验优先级排序 | failure=1.0 > lesson=0.8 > success=0.5 | memory.py L101 | Memory ✅ |
| 工具使用计数 | tools.usage_count++ | tools.py bump_usage() | Capability ✅ |

## 缺失（Evolution 层面）

| 能力 | 说明 | 严重度 |
|------|------|--------|
| **Feedback 系统** | 无用户反馈收集 (👍/👎) | 🔴 |
| **Reflection 引擎** | 不对失败原因进行分析 | 🔴 |
| **Learning 机制** | 不从经验中自动学习 | 🔴 |
| **Optimization 建议** | 不生成改进建议 | 🔴 |
| **Skill Update** | 不更新工具/技能 | 🔴 |
| **Capability Growth** | 不自动发现新能力 | 🔴 |
| **Auto-Fix** | 不自动修复发现的问题 | 🔴 |
| **AB Testing** | 无实验对比 | 🟢 |
| **Metrics 分析** | 不对系统指标做因果分析 | 🟡 |
| **Governor 联动** | Evolution 提建议但需 Governor 批准 | 🔴 |

---

## 当前"学习"流程（非 Evolution）

```
Session Close → LLM summarise → experiences:
  - kind: success / failure / lesson
  - title + content

新 Session → render_injection_for_new_session():
  - "【上次的关键事实】"  → 相关性召回
  - "【避免重复的失败】"  → 经验注入 Prompt
  - "【已验证的成功】"    → 经验注入 Prompt

这就是全部"学习" → 只是 Memory 召回，不改变任何系统行为
```
