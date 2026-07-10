"""MBOS TokenPool — interface protocol.

TokenPoolProtocol defines the contract for TokenPool implementations.
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class TokenPoolProtocol(Protocol):
    """Acquire available LLM candidates."""

    def acquire(self) -> list:
        ...
