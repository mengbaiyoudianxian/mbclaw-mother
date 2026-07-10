"""MBOS Runtime — Pub/Sub EventBus v2.

EventBus provides publish/subscribe event routing between MBOS modules.
This is a synchronous, per-instance bus — NOT a global singleton.

V2 upgrades from V1:
  - Typed event classes (replacing string event_type matching)
  - subscribe(event_class, handler) API
  - publish(event) auto-detects event type
  - Handler isolation — one handler failure doesn't break others

Usage:
    bus = EventBus()
    bus.subscribe(GovernorDenyEvent, my_audit_handler)
    bus.publish(GovernorDenyEvent(event_id="1", rule_hit="no_token_leak"))
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Callable, Type

from .event import Event

logger = logging.getLogger(__name__)

Handler = Callable[[Event], None]


class EventBus:
    """Per-runtime synchronous pub/sub event bus.

    Subscribers register interest in specific event types.
    Events are delivered synchronously to all matching subscribers.
    Handler failures are caught and logged — never propagated.

    Attributes:
        _subscriptions: Mapping from event class name to list of handlers.
    """

    def __init__(self):
        self._subscriptions: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event_class: Type[Event],
                  handler: Handler) -> None:
        """Register a handler for a specific event type.

        Args:
            event_class: The Event subclass to subscribe to.
            handler: Callable(event) → None. Return value discarded.
        """
        event_type = event_class.__name__
        self._subscriptions[event_type].append(handler)
        logger.debug("EventBus: subscribed to %s (total: %d)",
                     event_type, len(self._subscriptions[event_type]))

    def unsubscribe(self, event_class: Type[Event],
                    handler: Handler) -> None:
        """Remove a previously registered handler."""
        event_type = event_class.__name__
        try:
            self._subscriptions[event_type].remove(handler)
            logger.debug("EventBus: unsubscribed from %s", event_type)
        except ValueError:
            pass

    def publish(self, event: Event) -> None:
        """Deliver an event to all registered subscribers.

        Handlers are called synchronously in registration order.
        Exceptions in any handler are caught and logged — they never
        propagate to the caller or affect other handlers.

        Args:
            event: The Event instance to publish.
        """
        event_type = type(event).__name__
        handlers = self._subscriptions.get(event_type, [])

        if not handlers:
            return

        logger.debug("EventBus: publishing %s to %d handler(s)",
                     event_type, len(handlers))

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(
                    "EventBus: handler %s failed for %s: %s",
                    handler.__name__, event_type, e,
                )

    def subscriber_count(self, event_class: Type[Event]) -> int:
        """Return number of subscribers for an event type."""
        return len(self._subscriptions.get(event_class.__name__, []))

    def clear(self) -> None:
        """Remove all subscriptions."""
        self._subscriptions.clear()
