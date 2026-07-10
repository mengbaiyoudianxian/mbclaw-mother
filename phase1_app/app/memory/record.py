"""MBOS Memory — record types.

MemoryRecord represents a stored memory entry.
"""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MemoryRecord:
    """A single memory entry.

    Attributes:
        content: Memory text content.
        session_id: Owning session identifier.
        metadata: Additional context data.
        created_at: Timestamp of creation.
    """
    content: str
    session_id: int = 0
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
