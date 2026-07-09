# 任务一：当前已承担 Governor 职责的代码

> 精确盘点所有隐式的"Governor"行为

---

## 1. 已存在的 Governor 行为

### A. 工具安全分级（tools.py）

| 分类 | 名称 | 当前行为 | 问题 |
|------|------|---------|------|
| STABLE_TOOL_NAMES | read_file, list_directory, search_memory 等 9 个 | 标记 runtime="server"，无条件执行 | 无限制任何人调 LLM 就能读任何文件 |
| HIGH_IMPACT_TOOL_NAMES | write_file, edit_file, run_command 等 8 个 | 标记 runtime="admin"，但未强制执行权限 | execute() 中未检查 admin，仅标记了 status |
| DEVICE_TOOL_NAMES | 35 个设备工具 | 标记 runtime="device-remote"，执行前检查 collect_enabled + 心跳 | 设备操作需要设备在线 + 收集开关，这是正确的 |
| device-collect | export_photos/wechat/conversations | _device_collect_enabled() 检查收集开关 | 正确但缺少日志审计 |

### B. 命令黑名单（tool_runtime.py）

| 规则 | 文件 | 行 | 当前行为 |
|------|------|-----|---------|
| `self.blocked` | tool_runtime.py:6 | 6 条规则：rm -rf /, shutdown, reboot, fork bomb, mkfs, dd if= | 子字符串匹配，匹配到则返回 [BLOCKED] |
| `_allow()` | tool_runtime.py:44 | 遍历 blocked 列表，任意匹配即拒绝 | 简单可靠，但缺少审计日志 |

### C. 设备远程执行限制（tools.py）

| 检查项 | 函数 | 当前行为 |
|--------|------|---------|
| collect_enabled | _device_collect_enabled() | 检查设备心跳 → collect_enabled 标记 |
| 设备在线 | _device_heartbeat() | 最近 10 分钟内有心跳 |
| Root 权限 | device.permissions.root | 仅展示，不限制 |

### D. Admin 认证（admin/router.py）

| 检查 | 函数 | 当前行为 |
|------|------|---------|
| Session 验证 | _check_session() | Cookie token → JSON 文件校验 |
| 密码验证 | _verify_password() | SHA256(salt:pwd) 比对 |
| 依赖注入 | require_admin() | FastAPI Depends，401 拒绝 |

### E. LLM Provider 调度（mother_runtime.py）

| 行为 | 代码 | 位置 |
|------|------|------|
| Provider 优先级 | ['custom','zhipu','deepseek-cn','miclaw-bridge'] | _build_candidates() L283 |
| 故障转移 | for ... in candidates[:4] | run() L215 |
| 错误容限 | error_count >= 2 → abort | run() L234-236 |

---

## 2. 缺失的 Governor 职责

| 职责 | 当前状态 | 后果 |
|------|---------|------|
| **统一权限模型** | 散落在 4 个文件 | 无法全局控制 |
| **操作审计日志** | 无 | 无法追溯谁做了什么 |
| **危险操作拦截** | 仅 tool_runtime 的 6 条 | run_command、write_file 无限制 |
| **限额/配额** | 无 | 无限调用 LLM/工具 |
| **Checkpoint/Rollback** | 无 | 失败无法恢复 |
| **Task Abort** | 仅 max_turns=5 | 没有超时终止、没有用户取消 |
| **操作审批流** | 无 | LLM 自主决定一切 |
| **风险评分** | 无 | 不知道当前操作有多危险 |

---

## 3. 重复的 Governor 行为

| 行为 | 位置 1 | 位置 2 | 问题 |
|------|--------|--------|------|
| 工具运行时判断 | tools.py _tool_status() | tools.py STABLE/HIGH/DEVICE 集合 | 同一逻辑两份数据 |
| 命令安全检查 | tool_runtime.py _allow() | tools.py 无 | MotherRuntime 绕过 tool_runtime 直接调 execute() |
| 故障转移 | mother_runtime.py _build_candidates() | providers.py get_best_client() | 两套 fallback 逻辑 |

---

## 4. 冲突

| 冲突 | 描述 |
|------|------|
| **tool_runtime._allow() vs tools.execute()** | tool_runtime 有黑名单，但 execute() 不经过 tool_runtime |
| **MotherRuntime 绕过 Admin** | MotherRuntime.run() 无任何权限检查，LLM 可调任何工具 |
| **agent_run 绕过 Provider 调度** | agent_run 直接用传入的 llm 参数，不经过 _build_candidates() |
| **STABLE/HIGH 标记未生效** | _tool_status() 的返回值仅在 _tool_row() 展示，execute() 不检查 |
