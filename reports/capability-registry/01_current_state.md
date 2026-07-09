# Capability Registry 完整分析

> Task 01 | 只分析 Tool 系统 | 不开发
> 日期: 2026-07-09

---

## 1. MBclaw 当前 Tool 生命周期

### 1.1 注册流程

```
启动时 seed_tools()
    │
    ▼
BUILTIN_TOOLS (30个硬编码 dict)
    │
    ▼
遍历 dict → 检查数据库是否存在 → 不存在则 INSERT INTO tools
    │
    ▼
工具就绪 (在 tools 表中, id/name/category/summary/tags/description/parameters/examples/usage_count)
```

### 1.2 发现流程

```
用户/LLM → GET /tools (按 category/tag 过滤)
         → GET /tools/search?q=xxx (数据库 LIKE 搜索)
         → GET /tools/{id} (单条详情)
```

### 1.3 执行流程

```
POST /tools/execute {tool_name, content}
    │
    ▼
tools.execute(db, tool_name, content)
    │
    ├── _tool_status() → 判断 runtime 级别 (server/admin/device-remote/planned)
    │
    ├── 巨型 if/elif 链 (30个分支)
    │   ├── read_file/write_file/edit_file → 文件操作
    │   ├── run_command → subprocess
    │   ├── search_memory/list_sessions/get_session → memory
    │   ├── web_search/open_url → web
    │   ├── get_device_info/get_clipboard/set_clipboard → device
    │   ├── classify_content/extract_keywords/summarize_text → classification
    │   ├── device_* 工具 → device_tool_execute() → _device_collect_enabled/_device_heartbeat
    │   └── 其他 → 返回错误
    │
    ▼
bump_usage() → usage_count++
    │
    ▼
返回结果字符串
```

### 1.4 当前问题

```
注册 (硬编码)        vs  设计目标 (动态注册)
执行 (巨型if/elif)    vs  设计目标 (分派器)
搜索 (数据库LIKE)     vs  设计目标 (向量+全文)
参数 (JSON字符串)      vs  设计目标 (Typed Schema)
状态 (_tool_status)   vs  设计目标 (生命周期状态机)
统计 (usage_count)    vs  设计目标 (多维统计)
```

### 1.5 关键文件清单

```
app/tools.py        428行  核心: 注册 + 发现 + 执行 (全在一个文件)
app/skills.py       333行  GitHub/SSH skill + LLM_SKILL_PROMPTS (21个prompt-only skill)
app/tool_runtime.py  79行  MBOS ToolRuntime v1 (独立 parser + 黑名单 + 4类执行)
app/models.py         27行  Tool ORM 模型 (9个字段)
app/api.py             6行  4个端点 (GET /tools, GET /tools/search, GET /tools/{id}, POST /tools/execute)
```

### 1.6 问题汇总

| 问题 | 位置 | 影响 |
|------|------|------|
| 硬编码注册 | tools.py BUILTIN_TOOLS | 新增工具必须改代码+重启 |
| 巨型if/elif执行 | tools.py execute() 100行 | 不可测试、不可扩展 |
| Tool/Skill 分裂 | tools.py vs skills.py | 两套注册+两套执行 |
| LLM prompt注入 | skills.py LLM_SKILL_PROMPTS | 21个prompt作为纯文本注入SystemPrompt |
| 无Schema校验 | tools.py parameters JSON字符串 | 无类型检查、无自动文档 |
| 无生命周期 | 无安装/卸载/升级/禁用 | 只能增，不能减 |
| 与APK ToolRegistry不一致 | 两套代码 | 维护成本翻倍 |
| 无插件机制 | 所有工具内置 | 无法第三方扩展 |
