"""MBOS Capability — interface protocol.

CapabilityProtocol defines the contract for Capability implementations.
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class CapabilityProtocol(Protocol):
    """Register and execute tools."""

    def register(self, tool) -> None:
        ...

    def execute(self, name: str, arguments: str) -> dict:
        ...

    def list_tools(self) -> list:
        ...
