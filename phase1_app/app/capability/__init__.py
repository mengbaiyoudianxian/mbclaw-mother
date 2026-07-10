"""MBOS Capability v1 — tool execution layer.

Capability is the tool registry. Runtime bootstraps tools at init time
and dispatches tool execution through Capability.execute().
"""
from .capability import Capability
from .tool import ToolDefinition
from .interfaces import CapabilityProtocol

__all__ = ["Capability", "ToolDefinition", "CapabilityProtocol"]
