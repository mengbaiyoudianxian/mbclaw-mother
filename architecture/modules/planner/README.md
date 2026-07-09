# Planner — 决策层

## 一句话定位
分析用户意图，决定是否需要工具、选哪个工具。

## 职责
- 分析用户消息意图（chat / command / tool_request）
- 决定是否需要调用 Capability
- 选择最合适的 Capability

## 接口规范

```python
class Planner:
    def analyze_intent(message: str, context: dict) -> Intent: ...
    def select_capability(intent: Intent, capabilities: list[CapabilityDef]) -> CapabilityDef | None: ...

@dataclass
class Intent:
    type: Literal["chat", "tool_request", "ambiguous"]
    confidence: float
    suggested_tool: str | None
    reasoning: str
```

## 决策逻辑

```
用户消息 → analyze_intent()
    ├── 明确技能名 ("帮我code review这段代码") → tool_request, suggested=code-review
    ├── 明确操作 ("打开微信", "执行XX命令") → tool_request, suggested=open_app/run_command
    ├── 纯问题 ("Python 新特性?") → chat
    └── 模糊 → ambiguous (让 LLM 自己决定)
```

## 依赖
- Context Engine (上下文辅助判断)
- Capability (获取可用能力列表)

## 代码复用
当前隐式在 system prompt 中。需新建此模块，将意图分析从 prompt 提取为代码逻辑。
