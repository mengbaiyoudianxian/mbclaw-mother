"""MBOS Scheduler — interface protocol.

SchedulerProtocol defines the contract for Scheduler implementations.
Migrated from runtime/interfaces.py (Task 14).
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class SchedulerProtocol(Protocol):
    """Future: dispatch LLM execution."""

    def dispatch(self, messages: list[dict], llm_client=None) -> tuple:
        ...
