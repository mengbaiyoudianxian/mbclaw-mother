"""MBOS Memory — interface protocol.

MemoryProtocol defines the contract for Memory implementations.
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class MemoryProtocol(Protocol):
    """Save and query memory records."""

    def save(self, record) -> None:
        ...

    def query(self, session_id: int, limit: int = 10) -> list:
        ...
