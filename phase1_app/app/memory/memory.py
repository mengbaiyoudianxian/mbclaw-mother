"""MBOS Memory v1 — in-memory memory store.

Memory provides save() and query() for long-term data.
V1: in-memory list. No database, no vector store, no embedding.
"""
from .record import MemoryRecord


class Memory:
    """V1 in-memory memory store.

    Usage:
        mem = Memory()
        mem.save(MemoryRecord(content='hello', session_id=1))
        results = mem.query(session_id=1, limit=10)
    """

    def __init__(self):
        self._records: list[MemoryRecord] = []

    def save(self, record: MemoryRecord) -> None:
        """Store a memory record."""
        self._records.append(record)

    def query(self, session_id: int, limit: int = 10) -> list[MemoryRecord]:
        """Query records by session_id, newest first, limited."""
        result = []
        for r in reversed(self._records):
            if r.session_id == session_id:
                result.append(r)
            if len(result) >= limit:
                break
        return list(reversed(result))
