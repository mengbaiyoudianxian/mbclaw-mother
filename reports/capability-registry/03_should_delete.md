# 3. 应该删除的代码

## 硬编码注册 → 全部删除

```
BUILTIN_TOOLS = [...]  (90行 dict 列表)
STABLE_TOOL_NAMES       (5行 set)
HIGH_IMPACT_TOOL_NAMES  (3行 set)
DEVICE_TOOL_NAMES       (10行 set)
```

**原因**: 新增工具必须修改 Python 代码。应该从配置文件加载。

## 巨型执行函数 → 全部重构

```
tools.py execute()      (130行 if/elif/else)
skills.py execute_skill() (90行 if/elif)
```

**原因**: 每加一个工具要加一个 elif 分支。不可测试。不可扩展。

## Tool/Skill 分裂 → 统一

```
tools.py:  30个"工具" (有execute实现)  → 统一为 Capability
skills.py: 12个GitHub skill (有execute) → 统一为 Capability
skills.py: 21个prompt skill (只注入prompt) → 统一为 Capability (type=prompt_skill)
```

**原因**: 三套不同的执行路径，LLM 需要知道哪个是 tool 哪个是 skill。

## 重复 Registry → 删除旧的

```
tools.py: _tool_row() + list_tools() + search_tools() + get_tool() + get_tool_by_name()
           → 第一个 Registry

skills.py: execute_skill() if/elif 链 → 隐式 Registry（硬编码在 if 语句中）

tool_runtime.py: ToolRuntime._parse() → 第三个独立的解析+执行
```

**原因**: 三个地方都在做"注册→查找→执行"，但互不兼容。

## 废弃代码 → 删除

```
skills.py: api_placeholder()         → 空壳函数
skills.py: _PLACEHOLDER 列表         → 无实现
tool_runtime.py: 整个 ToolRuntime    → 已被 tools.py 覆盖
```

## 删除后的文件状态

| 文件 | 删除后保留 | 行数变化 |
|------|-----------|---------|
| app/tools.py | 无 (或 rename → capabilities/registry.py) | 428→0 |
| app/skills.py | 无 (GitHub/SSH 函数移入 capabilities/skills/) | 333→0 |
| app/tool_runtime.py | 无 | 79→0 |
| app/models.py | Tool 模型保留+扩展 | 27→35 |
| app/api.py | 4个端点保留 | 6→4 |
