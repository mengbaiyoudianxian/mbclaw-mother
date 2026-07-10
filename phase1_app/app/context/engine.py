"""MBOS Context Engine v2 — dynamic capability prompt.

ContextEngine builds LLM messages from session WorkingMemory.
System prompt + dynamic tool list from Registry + recall + conversation history.

v2: Tool list generated from ToolRegistry (no hardcoded "42 skills").
"""
from .working_memory import WorkingMemory


SYSTEM_PROMPT_BASE = """你是"母体-小梦"，由孟白创造的 AI 助手，通过 QQ 和用户交互。

## 聊天原则
优先直接回应用户的提问。只在以下情况用工具:
- 用户明确要求执行操作(执行命令、查系统状态、GitHub操作等)
- 需要查文件或记忆
- 用户要求查看MBOS运行状态(使用 control_plane 工具)

严禁为自我介绍、问候、闲聊使用任何工具。
始终用中文回复，短小精炼，三句话以内。

工具格式: <tool>名称</tool><content>参数</content>
每轮最多一个工具。收到结果后直接回复，禁止继续调工具。

"""


def _build_tool_prompt(registry) -> str:
    """Generate dynamic tool list from Capability Registry."""
    if registry is None:
        return "无工具可用。"
    return registry.format_for_agent()


class ContextEngine:
    """V2 context builder — dynamic tool list from Registry."""

    def __init__(self, tool_registry=None):
        self._registry = tool_registry
        self.system_prompt = SYSTEM_PROMPT_BASE

    def set_registry(self, registry):
        """Late-bind registry (avoids circular import in __init__)."""
        self._registry = registry

    def build(self, message: str, session_id: int,
              wm: WorkingMemory) -> list[dict]:
        """Build LLM messages with dynamic tool list."""
        if not wm.system:
            tool_prompt = _build_tool_prompt(self._registry)
            full_prompt = self.system_prompt + tool_prompt
            wm.set_system(full_prompt)
        return wm.to_messages()
