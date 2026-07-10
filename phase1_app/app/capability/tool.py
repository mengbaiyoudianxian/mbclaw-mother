"""MBOS Capability — tool types.

ToolDefinition represents a registered tool.
"""
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ToolDefinition:
    """A tool registered in the Capability registry.

    Attributes:
        name: Unique tool identifier.
        description: Human-readable tool description.
        handler: Callable that executes the tool. Receives argument string,
                 returns result string.
        metadata: Optional additional data.
    """
    name: str
    description: str
    handler: Callable[[str], str]
    metadata: dict = field(default_factory=dict)
