# 4. 最终统一方案

## CapabilityRegistry 统一模型

所有功能（Tool / Skill / MCP / Plugin / LLM Prompt）统一为 **Capability**：

```
Capability
├── type: "tool" | "skill" | "prompt_skill" | "mcp_tool" | "plugin"
├── name: str            (唯一标识)
├── description: str     (LLM 可读描述)
├── category: str        (分组: file/shell/memory/web/device/...)
├── tags: list[str]      (多标签)
├── input_schema: dict   (JSON Schema, MCP 对齐)
├── executor: callable   (执行函数)  -- tool/skill/mcp
├── prompt: str          (注入 System Prompt) -- prompt_skill
├── runtime: str         (server/admin/device-remote/planned)
├── usage_count: int     (调用次数)
├── enabled: bool        (启用/禁用)
└── version: str         (版本号)
```

## 统一后的目录

```
capabilities/
├── registry.py          # 核心注册表
│   ├── class CapabilityDef     (数据类)
│   ├── class CapabilityRegistry
│   │   ├── register(cap: CapabilityDef)
│   │   ├── get(name) → CapabilityDef
│   │   ├── list(category, tag) → list
│   │   ├── search(query) → list
│   │   ├── execute(name, **params) → result
│   │   └── enable/disable(name)
│   └── REGISTRY: dict[str, CapabilityDef]
│
├── models.py            # ORM
│   └── class Capability(Base)
│       # 扩展当前 Tool 模型:
│       # + capability_type, input_schema(json),
│       #   enabled, version, runtime
│
├── loader.py            # 启动加载器
│   ├── load_builtin()           (从 builtins/ 目录加载 .yml)
│   ├── load_from_db()           (从数据库恢复)
│   └── seed_defaults()          (首次启动写入)
│
├── executor.py          # 执行引擎
│   ├── def execute(name, params) → result
│   ├── class SecurityPolicy    (allow/deny/ask)
│   ├── def bump_usage(name)
│   ├── def device_tool_execute()
│   └── def device_heartbeat()
│
├── search.py            # 搜索
│   ├── def search(query) → FTS5 + jieba
│   └── def suggest(query) → 模糊匹配
│
├── publisher.py         # 对外发布
│   ├── def to_llm_tools() → OpenAI tool format
│   ├── def to_mcp_tools() → MCP tools/list 格式
│   ├── def to_system_prompt() → LLM prompt
│   └── def to_api_response() → API 返回
│
├── validator.py         # 校验
│   ├── def validate_name(name)
│   ├── def validate_schema(input_schema, params)
│   └── def validate_capability(cap: CapabilityDef)
│
├── runtime.py           # 运行时状态
│   ├── class RuntimeState (server/admin/device/offline)
│   ├── def check_runtime(name) → status
│   └── def is_executable(name) → bool
│
└── builtins/            # 内置能力定义 (YAML, 不是 Python)
    ├── files.yml        (read_file, write_file, edit_file, list_directory)
    ├── shell.yml        (run_command)
    ├── memory.yml       (search_memory, list_sessions, get_session)
    ├── web.yml          (web_search, open_url)
    ├── device.yml       (get_device_info, get_clipboard, set_clipboard, take_screenshot)
    ├── device_collect.yml (export_photos, export_wechat, export_conversations, ...)
    ├── classification.yml (classify_content, extract_keywords, summarize_text)
    └── skills/
        ├── github.yml   (12个 GitHub API)
        ├── ssh.yml      (ssh_exec)
        └── prompts.yml  (21个 prompt_skill)
```

## 统一带来的好处

| Before | After |
|--------|-------|
| 3个文件定义工具 (tools/skills/tool_runtime) | 1个目录统一管理 |
| 硬编码 Python dict/if 链 | YAML 声明 + Registry 查找 |
| Tool / Skill / Prompt 三套逻辑 | 统一 Capability 接口 |
| 新增工具改代码重启 | 新增 .yml + 热加载 |
| 无参数校验 | JSON Schema 自动校验 |
| 无 LLM Tool 格式导出 | publisher.py 一键生成 OpenAI/MCP format |
