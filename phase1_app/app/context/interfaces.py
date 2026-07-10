"""MBOS Context Engine — interface protocol.

ContextEngineProtocol defines the contract for context builders.
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class ContextEngineProtocol(Protocol):
    """Build LLM messages from session context."""

    def build(self, message: str, session_id: int, memory) -> list[dict]:
        ...
