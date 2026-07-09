# 2. 哪些代码可以直接复用？

> 只列出文件/类/函数 | 不复制 | 不执行

---

## MBclaw 内部可保留

| 文件 | 类/函数 | 原因 | 保留方式 |
|------|---------|------|---------|
| app/models.py | `Tool` ORM 类 | 数据库映射完整，9个字段基本合理 | 增加字段(capability_type, input_schema, status, version) |
| app/models.py | `ModelProfile` ORM 类 | 独立，不需要改 | 保持原位 |
| app/tools.py | `_tool_row()` | 格式化输出，可用于 registry.list() | 移入 registry.py |
| app/tools.py | `bump_usage()` | 使用统计，简单可用 | 移入 executor.py |
| app/tools.py | `search_tools()` | 数据库搜索逻辑 | 移入 registry.py，改用 FTS |
| app/tools.py | `seed_tools()` | 启动时初始化 | 移入 loader.py |
| app/tools.py | `_device_tool_execute()` | 设备工具分发 | 移入 executor.py |
| app/tools.py | `_device_heartbeat()` | 设备心跳查询 | 移入 executor.py |
| app/tools.py | `_device_collect_enabled()` | 收集开关检查 | 移入 executor.py |
| app/skills.py | `github_*()` 所有函数 | 12个GitHub API函数完整可用 | 移入 capabilities/skills/github.py |
| app/skills.py | `ssh_exec()` | SSH远程执行 | 移入 capabilities/skills/ssh.py |
| app/skills.py | `execute_skill()` | 技能分派逻辑 | 移入 executor.py，改为注册表查找 |
| app/skills.py | `LLM_SKILL_PROMPTS` | 21个prompt skill | 移入 capabilities/skills/prompts.py |
| app/tool_runtime.py | `ToolRuntime._allow()` | 黑名单检查 | 移入 executor.py 的 security policy |
| app/tool_runtime.py | `ToolRuntime._parse()` | `<tool_call>` 解析 | 移入 runtime.py |

## 参考项目可直接借鉴

| 来源 | 文件 | 类/函数 | 借鉴什么 |
|------|------|---------|---------|
| **MCP SDK** | `tools/base.py` | `Tool(BaseModel)` | Tool schema: name, description, inputSchema(JSON Schema), annotations |
| **MCP SDK** | `tools/tool_manager.py` | `ToolManager` | 工具注册/查找/列表管理 |
| **MCP SDK** | `shared/tool_name_validation.py` | `validate_and_warn_tool_name()` | 工具名验证 |
| **OpenClaw** | `channels/plugins/catalog.ts` | `listChannelCatalogEntries()` | 插件目录构建 |
| **OpenClaw** | `channels/plugins/types.public.ts` | `ChannelMeta` | 插件元数据类型 |
| **OpenClaw** | `channels/plugins/registry-loaded.ts` | PluginRegistry | 已加载插件注册表 |
| **OpenHands** | `app_server/services/injector.py` | `Injector` | 依赖注入(工具注册) |
| **Claude** | (文档) Tool Use API | `input_schema` JSON Schema | 参数校验格式 |
| **OpenAI** | (文档) Function Calling | `function.parameters` type:object | 参数声明格式 |

## 可删除

| 文件/函数 | 位置 | 原因 |
|-----------|------|------|
| `BUILTIN_TOOLS` 硬编码列表 | tools.py:45-134 | 改为动态注册 |
| `execute()` 巨型if/elif | tools.py:291-422 | 改为 dispatcher + registry |
| `_tool_status()` 静态判断 | tools.py:143-154 | 改为 runtime 字段 |
| `STABLE_TOOL_NAMES` | tools.py:20-23 | 合并入 capability 的 tags |
| `HIGH_IMPACT_TOOL_NAMES` | tools.py:25-27 | 合并入 capability 的 tags |
| `DEVICE_TOOL_NAMES` | tools.py:31-42 | 合并入 capability 的 category |
| `execute_skill()` if/elif 链 | skills.py:241-331 | 改为 registry.get(name).execute() |
| `ToolRuntime` 类 (MBOS) | tool_runtime.py | 功能已被 tools.py 覆盖 |
| `api_placeholder()` | skills.py:213 | 废弃，_PLACEHOLDER 列表可删除 |
