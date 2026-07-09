# 7. 哪些地方可以直接抄

> 精确到文件、类、函数。不模糊描述。

---

## MCP Python SDK — 直接抄

### 可以照搬的文件

| 文件 | 行数 | 抄什么 | 怎么用 |
|------|------|--------|--------|
| `mcp/src/mcp/server/mcpserver/tools/base.py` | ~80 | `class Tool(BaseModel)` 完整字段定义 | 作为 CapabilityDef 的字段蓝图 |
| `mcp/src/mcp/shared/tool_name_validation.py` | ~30 | `validate_and_warn_tool_name()` | 直接 import 或复制到 validator.py |

### Tool model 字段映射

```python
# MCP Tool (可逐字段翻译)
class Tool(BaseModel):
    name: str                          # → CapabilityDef.name
    description: str                   # → CapabilityDef.description
    parameters: dict[str, Any]         # → CapabilityDef.input_schema (JSON Schema)
    annotations: ToolAnnotations       # → CapabilityDef.tags + runtime
    icons: list[Icon]                  # → 可选 (Phase 2)
    meta: dict[str, Any]               # → CapabilityDef 的 extra 字段
```

**为什么**: MCP Tool 是行业标准格式。直接对齐避免重复发明。OpenAI/Claude 都兼容。

---

## OpenClaw — 借鉴（不照抄）

### 可以参考设计的文件

| 文件 | 功能 | 借鉴什么 | 为什么不照抄 |
|------|------|---------|-------------|
| `channels/plugins/catalog.ts` | `listChannelCatalogEntries()` | 插件目录构建 | TypeScript, MBclaw 不需要 npm registry |
| `channels/plugins/types.public.ts` | `ChannelMeta` 类型 | 插件元数据结构 | TypeScript, Python 用 dataclass |
| `channels/plugins/message-tool-api.ts` | 消息工具 API | 工具调用接口格式 | 通信协议不同 |

### 借鉴内容

```
OpenClaw Plugin Meta → MBclaw CapabilityDef 元数据:
  id → name
  displayName → summary (已有)
  description → description (已有)
  category → category (已有)
  permissions → runtime + tags
```

**为什么借鉴**: 插件元数据设计成熟，但 TypeScript 代码不能直接用。

---

## OpenAI Tool Calling — 直接抄格式

### JSON Schema (复制到 publisher.py)

```python
# publisher.py — 完全对齐 OpenAI Function Calling 格式
def to_openai_tools(capabilities: list[CapabilityDef]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": cap.name,
                "description": cap.description,
                "parameters": cap.input_schema,  # JSON Schema 格式
            }
        }
        for cap in capabilities
        if cap.enabled and cap.type in ("tool", "skill", "mcp_tool")
    ]
```

**为什么抄**: OpenAI 格式是所有 LLM Provider 的事实标准。

---

## Claude Tool Use — 抄参数校验

### input_schema 格式

```json
{
  "name": "read_file",
  "description": "读取文件内容",
  "input_schema": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "文件绝对路径"}
    },
    "required": ["path"]
  }
}
```

**为什么抄**: JSON Schema 校验是成熟的，validator.py 直接使用 `jsonschema` 库。

---

## 不抄的

| 项目 | 文件 | 原因 |
|------|------|------|
| OpenHands | openhands-sdk tools/ | SDK 是外部包，内部实现不可见 |
| Codex CLI | codex-rs/skills/ | Rust, 不兼容 Python |
| FreeLLMAPI | router.ts | TokenPool 用，不是 Capability |
| Mem0 | memory/main.py | Memory 用，不是 Tool |

## 总结: 抄什么、怎么抄

| 参考 | 抄什么 | 翻译到 | 优先级 |
|------|--------|--------|--------|
| MCP SDK | `Tool` Pydantic model 字段 | `CapabilityDef` dataclass | P0 |
| MCP SDK | `validate_and_warn_tool_name()` | `validator.py` | P0 |
| OpenAI | Function Calling JSON format | `publisher.to_openai_tools()` | P0 |
| Claude | `input_schema` JSON Schema 格式 | `builtins/*.yml` 格式 | P0 |
| OpenClaw | Plugin Meta 元数据结构 | `CapabilityDef` 字段 | P1 |
