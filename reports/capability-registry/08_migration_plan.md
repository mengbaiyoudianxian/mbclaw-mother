# 8. 最终迁移计划

> 只输出 Phase | 不执行 | 不写代码

---

## Phase 1 — 删除 + 创建目录 + Model

**目标**: 清理旧代码 + 建立新目录 + 更新数据库模型

### 删除

```
app/tools.py          → 删除 (移至 capabilities/)
app/skills.py         → 删除 (移至 capabilities/skills/)
app/tool_runtime.py   → 删除 (功能覆盖)
```

### 新增文件

```
capabilities/__init__.py
capabilities/models.py       ← 扩展 Tool 模型 → Capability 模型
  + capability_type: str     (tool/skill/prompt_skill/mcp_tool/plugin)
  + input_schema: JSON       (JSON Schema 格式)
  + enabled: bool            (替代软删除)
  + version: str
  + runtime: str             (替代 _tool_status)
  + updated_at: datetime
```

### 修改文件

```
app/models.py                ← 删除 Tool 类，新增 Capability 类
app/api.py                   ← 暂时保留 4 个端点 (兼容)
```

### DB 迁移

```
ALTER TABLE tools RENAME TO capabilities
ALTER TABLE capabilities ADD COLUMN capability_type TEXT DEFAULT 'tool'
ALTER TABLE capabilities ADD COLUMN input_schema TEXT DEFAULT '{}'
ALTER TABLE capabilities ADD COLUMN enabled INTEGER DEFAULT 1
ALTER TABLE capabilities ADD COLUMN version TEXT DEFAULT '1.0.0'
ALTER TABLE capabilities ADD COLUMN runtime TEXT DEFAULT 'server'
ALTER TABLE capabilities ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
```

### Phase 1 完成标准

- 旧文件删除
- 新目录建立
- DB 迁移完成
- 4 个 API 端点仍可用（兼容期）

---

## Phase 2 — Registry + Loader + Validator

### 新增文件

```
capabilities/registry.py     ← CapabilityDef + CapabilityRegistry
capabilities/loader.py       ← load_builtins() + load_from_db() + seed_first_run()
capabilities/validator.py    ← validate_name() + validate_schema() + validate_capability()
```

### 新增内容

```
builtins/files.yml           ← 5 个 file 工具移入 YAML
builtins/shell.yml           ← 1 个 shell 工具
builtins/memory.yml          ← 3 个 memory 工具
builtins/web.yml             ← 2 个 web 工具
builtins/device.yml          ← 4 个 device 工具
builtins/device_collect.yml  ← 5 个 device-collect 工具
builtins/classification.yml  ← 3 个 classification 工具
builtins/skills/github.yml   ← 12 个 GitHub 技能
builtins/skills/ssh.yml      ← 1 个 SSH 技能
builtins/skills/prompts.yml  ← 21 个 prompt_skill
```

### 修改文件

```
app/api.py                   ← GET /capabilities 指向 registry.list()
                            ← GET /capabilities/search 指向 registry.search()
                            ← GET /capabilities/{name} 指向 registry.get()
                            ← POST /capabilities/execute 指向 executor.execute()
```

### Phase 2 完成标准

- 全部 57 个 capability 从 YAML 加载
- Registry 内存注册表可以 list/get/search
- API 端点切换到新 Registry
- 旧的 tools.py 端点兼容（同时存在）

---

## Phase 3 — Executor + Publisher + Runtime

### 新增文件

```
capabilities/executor.py     ← execute() + SecurityPolicy
capabilities/publisher.py    ← to_openai_tools() + to_system_prompt() + to_mcp_tools()
capabilities/runtime.py      ← RUNTIME_MATRIX + check()
capabilities/search.py       ← FTS5 搜索 (替换 SQL LIKE)
```

### 执行器迁移

```
从 tools.py execute() 130 行 if/elif
    → executor.py execute() 30 行:
       1. registry.get(name)
       2. validator.validate(params)
       3. security.check(name, params)
       4. runtime.check(name)
       5. capability.executor(**params)
       6. bump_usage(name)
```

### 发布器

```
publisher.to_openai_tools():  旧代码在 agent.py 中手动拼接 → 自动生成
publisher.to_system_prompt(): 旧 LLM_SKILL_PROMPTS 硬编码文本 → 从 prompt_skill 动态生成
```

### Phase 3 完成标准

- execute() 通过 Registry 分发（不再有 if/elif）
- SecurityPolicy (allow/deny/ask) 生效
- OpenAI Tool format 自动生成
- System Prompt 从 prompt_skill 自动注入
- FTS5 搜索替换 SQL LIKE

---

## Phase 4 — Installer + 热加载 + APK 对接（远期）

### 新增文件

```
capabilities/installer.py    ← install() + uninstall() + upgrade()
capabilities/watcher.py      ← 文件变更检测 + hot_reload()
```

### APK 对接

```
移动端 ToolRegistry.kt → 改为从 Server capabilities/ 同步定义
  GET /capabilities/export/mobile → Android 格式
  统一 Tool 命名 (当前两端不一致)
```

---

## 迁移影响范围

| 文件 | Phase 1 | Phase 2 | Phase 3 | 最终 |
|------|---------|---------|---------|------|
| app/tools.py | ❌ 删除 | — | — | — |
| app/skills.py | ❌ 删除 | — | — | — |
| app/tool_runtime.py | ❌ 删除 | — | — | — |
| app/models.py | ✏️ 改 | — | — | 留存 |
| app/api.py | — | ✏️ 改 | — | 留存 |
| capabilities/ | ✨ 新建 | ✨ 新建 | ✨ 新建 | 10 文件 |
| builtins/ | — | ✨ 新建 | — | 10 YAML |
| DB | ✨ 迁移 | — | — | capability 表 |

## 工作量估算

| Phase | 内容 | 天数 |
|-------|------|------|
| Phase 1 | 删除 + 目录 + Model + DB 迁移 | 1 天 |
| Phase 2 | Registry + Loader + Validator + YAML | 2 天 |
| Phase 3 | Executor + Publisher + Runtime + Search | 2 天 |
| Phase 4 | Installer + 热加载 + APK 对接 | 远期 |
| **总计** | **Phase 1-3** | **5 天** |
