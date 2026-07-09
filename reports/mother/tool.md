# Mother Tool 分析

## 作用

Tool 层提供 Agent 的工具执行能力。Mother 有三套工具系统，功能重叠。

## 当前实现

涉及文件：`app/tools.py`（428 行）、`app/skills.py`（~305 行）、`app/tool_runtime.py`（80 行）

### tools.py — 主工具系统
**工具注册**：数据库 Tool 表 + 内存 BUILTIN_TOOLS 列表（25 个内置工具）

**工具分类**：
- STABLE（server 级）：read_file, list_directory, search_memory, list_sessions, get_session, get_device_info, classify_content, extract_keywords, summarize_text
- HIGH_IMPACT（admin 级）：write_file, edit_file, run_command, open_url, take_screenshot, get_clipboard, set_clipboard, web_search
- DEVICE（device-remote 级）：30+ Android 设备工具（WiFi、蓝牙、亮度、音量、截图、点击、滑动、应用管理、数据收集等）

**执行引擎**：if-elif 分支匹配工具名，直接调用对应实现

**设备工具**：通过 debug_commands 队列向心跳系统下发命令

### skills.py — 高级技能系统
**GitHub 全家桶**（14 个函数）：search_code, list_repos, get_pr, create_pr, list_issues, create_issue, get_file, list_workflows, workflow_runs, pr_review, pr_diff, compare, create_release

**SSH 远程执行**（ssh_exec）：基于 sshpass + 环境变量密码

**API 占位**（10 个）：gitlab, bitbucket, linear, jira, notion, datadog, vercel, discord, slack, azure_devops — 全部返回 Token 配置指引

**LLM 技能提示**（21 个）：code-review, code-simplifier, prd, security, frontend-design 等 — 纯 prompt 指令，嵌入系统提示，无代码执行

### tool_runtime.py — MBOS Core 工具运行时
独立工具执行器，被 MBOSCore 使用：
- shell：subprocess 执行命令
- system：查询系统信息（uname, cpu, memory, disk, uptime）
- read：读取文件
- 安全拦截列表：rm -rf /, shutdown, reboot 等

## 工具调用流程

```
用户消息
    ↓
MotherRuntime.run() / agent_run()
    ↓
<tool>名称</tool><content>参数</content> 正则解析
    ↓
_execute_tool(name, arg)
    ├── github_* / ssh_exec → skills.execute_skill()
    ├── gitlab_api 等 10 个 → skills.api_placeholder()
    └── 其他 25 个 → tools.execute()
        ├── read_file, write_file, edit_file, list_directory
        ├── run_command (subprocess)
        ├── search_memory, list_sessions, get_session
        ├── device_status → _device_heartbeat()
        └── device tools → device_tool_execute() → debug_commands
```

## 存在问题

1. **三套工具系统并存**：tools.py / skills.py / tool_runtime.py 各自独立
2. **if-elif 分支超过 30 个**：tools.execute() 是一大段 if-elif，O(n) 查找
3. **工具定义分散**：MotherRuntime.system_prompt 中硬编码 14 个工具，agent.py 中另有 7 个，tools.py 中有 25 个，skills.py 中有 35+ 个
4. **设备工具耦合到 debug_api_v2**：device_tool_execute 直接 import debug_api_v2 的内部变量
5. **GitHub 技能无认证检查**：每个函数独立检查 GITHUB_TOKEN，无统一拦截
6. **tool_runtime.py 的 JSON 解析与 MotherRuntime 的正则解析不一致**
7. **LLM_SKILL_PROMPTS 是纯文本**：未注册为可执行工具，全凭 LLM 自觉

## 建议

1. 统一工具注册表：一个 ToolRegistry，所有工具（含 GitHub、SSH、设备、LLM技能）都通过它注册和调度
2. execute() 改为 dict dispatch 或 ToolHandler 类层次
3. 工具定义集中管理：单一来源（数据库 + 代码），不再分散在 system prompt 各处
4. 设备工具解耦 debug_api_v2

## 以后是否保留

- **tools.py**：保留核心执行逻辑，重构为 ToolHandler 模式
- **skills.py**：保留 GitHub/SSH 实现，整合入统一工具注册表
- **tool_runtime.py**：废弃，合并入 tools.py
