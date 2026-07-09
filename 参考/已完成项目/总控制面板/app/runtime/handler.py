"""MBOS Runtime — Event handler base.

All handlers must implement this protocol.
Handlers are OBSERVERS ONLY:
  - Read event data.
  - Do NOT modify Runtime / ExecutionContext / Session / Result.
  - Return value is always discarded by EventBus.

Violation of this contract will be caught in code review.
"""
from typing import Protocol, runtime_checkable

from .event import Event


@runtime_checkable
class EventHandler(Protocol):
    """Read-only event observer.

    handle(event) → None.
    Must not mutate Runtime state.
    """

    def handle(self, event: Event) -> None:
        ...
