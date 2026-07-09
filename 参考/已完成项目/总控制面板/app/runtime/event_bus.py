"""MBOS Runtime — synchronous EventBus.

NOT a global singleton. Each MotherRuntime instance owns its own bus.
Handlers are read-only observers — return values are discarded.

Usage:
    bus = EventBus()
    bus.register("request", my_handler)
    bus.emit(RequestEvent(...))
"""
from collections import defaultdict
from typing import Callable

from .event import Event


class EventBus:
    """Per‑runtime synchronous event bus.

    Handlers receive events for notification only.
    They MUST NOT modify Runtime state, ExecutionContext, or Session.
    All handler return values are discarded.
    """

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def register(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Register a handler for a specific event_type.

        handler(event) → None. Return value is always discarded.
        """
        self._handlers[event_type].append(handler)

    def unregister(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Remove a previously registered handler."""
        try:
            self._handlers[event_type].remove(handler)
        except ValueError:
            pass

    def emit(self, event: Event) -> None:
        """Deliver event to all registered handlers.

        Failures in any single handler are caught and do not
        propagate — the Runtime must never break because of an observer.
        """
        for handler in self._handlers.get(event.event_type, []):
            try:
                handler(event)
            except Exception:
                pass

    def clear(self) -> None:
        """Remove all handlers (e.g. on Runtime reset)."""
        self._handlers.clear()
