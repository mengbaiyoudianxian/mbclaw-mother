# 任务一：当前 Scheduler 盘点

## 结论：MBclaw 有三个隐式 Scheduler，但都不是正式 Scheduler

---

## A. 已存在（但散落）

### 1. LLM Provider 选择（mother_runtime.py `_build_candidates`）

```
职责: 从 TokenPool 选取 LLM key 候选列表
优先级: custom > zhipu > deepseek-cn > miclaw-bridge > 其他
排序: working 状态优先
输出: [(base_url, api_key, model), ...]
```

| 属性 | 值 |
|------|-----|
| 属于 Scheduler | ✅ Provider 选择 |
| 是否正式 | ❌ 内嵌在 MotherRuntime 私有方法中 |
| 问题 | 硬编码 provider 优先级，不可配置 |

### 2. LLM 调用重试（mother_runtime.py `run()` for loop）

```
职责: HTTP 调用失败后逐个尝试候选 key
重试: 最多 4 个候选，遍历 candidates[:4]
策略: 任意 200 → 成功；全部失败 → error_count++
容限: error_count >= 2 → 中止
超时: 15s (agent_run 是 120s)
```

| 属性 | 值 |
|------|-----|
| 属于 Scheduler | ✅ 重试 + 故障转移 |
| 是否正式 | ❌ 内嵌在 run() 方法中 |
| 问题 | 无指数退避、无 429 识别、无 cooldown |

### 3. Provider 优先级（providers.py `get_best_client`）

```
职责: 从 DB 读取 ModelProfile，按 priority 排序
策略: 逐条检查 api_key_env 环境变量
输出: LLMClient 实例
```

| 属性 | 值 |
|------|-----|
| 属于 Scheduler | ✅ Provider 选择（但 agent_run 不用它） |
| 是否正式 | 半正式（独立函数，但未被 agent_run 使用） |
| 问题 | 与 _build_candidates 功能重复 |

---

## B. 属于 Scheduler 但未被识别的

| 行为 | 位置 | 当前归属 | 应归 Scheduler |
|------|------|---------|---------------|
| 工具路由 (if/elif) | tools.py execute() 130行 | tools.py | Scheduler.dispatch() |
| LLM API 调用 | agent.py:httpx | agent.py | Scheduler.call_llm() |
| TokenPool key 筛选 | mother_runtime.py _build_candidates | mother_runtime | Scheduler.select_provider() |
| bump_usage | tools.py bump_usage() | tools.py | Scheduler.metrics() |
| LLM mock 模式 | agent.py:118 | agent.py | Scheduler.mock_mode() |

---

## C. 属于 Runtime 不是 Scheduler 的

| 行为 | 位置 | 为什么属于 Runtime |
|------|------|-------------------|
| Agent Loop (while/for) | agent.py + mother_runtime.py | 执行流程控制 |
| 上下文构建 | _build_context() + WorkingMemory.to_messages() | 上下文管理 |
| 工具结果追加 | wm.add("user", tool_result) | 对话管理 |
| System Prompt 构建 | AGENT_PROMPT.format() | Prompt 管理 |

---

## D. 属于 TokenPool 不是 Scheduler 的

| 行为 | 位置 | 为什么属于 TokenPool |
|------|------|--------------------|
| Key 存储/加载 | token_pool.py TokenPool._load() | 数据层 |
| Key 状态 (working/failed) | PoolKey.status | 数据层 |
| usage_count 统计 | PoolKey.usage_count | 数据层 |

---

## E. 完全缺失的 Scheduler 能力

| 能力 | 说明 | 严重度 |
|------|------|--------|
| Worker 选择 | 无 Worker 概念，直接调函数 | 🔴 高 |
| LLM Router | 无统一路由，3 处各自调 httpx | 🔴 高 |
| 429 识别 | 不区分 429 / 5xx / timeout | 🟡 中 |
| 速率限制 | 无限调用 | 🟡 中 |
| 指数退避 | 无延迟重试 | 🟡 中 |
| Cooldown | 失败的 key 下次还会试 | 🔴 高 |
| 健康检查 | 无主动探测 | 🟡 中 |
| 负载均衡 | 无 Round-Robin | 🟡 中 |
| 并发限制 | 无 | 🟢 低 |
| 优先级队列 | 无 | 🟢 低 |

---

## 冲突

| 冲突 | 描述 |
|------|------|
| **providers vs mother_runtime** | 两套独立的 Provider 选择，互不知道 |
| **agent_run 绕过所有人** | 直接 httpx，不经过 providers 也不经过 mother_runtime |
| **llm.py fallback vs token_pool** | LLMClient 有自己的 token_pool fallback，mother_runtime 也有 |
