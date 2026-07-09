"""MBOS Capability v1 — tool registry and executor.

Capability holds registered tools and dispatches execution.
V1: manual registration. No auto-discovery, no sandbox, no permissions.
"""
from .tool import ToolDefinition


class Capability:
    """V1 tool registry.

    Tools are registered by name and dispatched on execute().
    Runtime bootstraps tools via register() at init time.

    Usage:
        cap = Capability()
        cap.register(ToolDefinition(name='echo', description='...', handler=my_fn))
        result = cap.execute('echo', 'hello')
    """

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._fallback = None

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool definition."""
        self._tools[tool.name] = tool

    def set_fallback(self, handler) -> None:
        """Set a fallback handler for unregistered tools.

        Args:
            handler: Callable(name: str, arg: str) -> str.
        """
        self._fallback = handler

    def list_tools(self) -> list[ToolDefinition]:
        """Return all registered tool definitions."""
        return list(self._tools.values())

    def execute(self, name: str, arguments: str) -> str:
        """Execute a registered tool by name.

        Args:
            name: Tool name to execute.
            arguments: Raw argument string passed to handler.

        Returns:
            Handler result string, or error message string.
        """
        tool = self._tools.get(name)
        if tool is not None:
            try:
                return tool.handler(arguments)
            except Exception as e:
                return f"工具错误: {e}"
        if self._fallback is not None:
            try:
                return self._fallback(name, arguments)
            except Exception as e:
                return f"工具错误: {e}"
        return f"工具未找到: {name}"
