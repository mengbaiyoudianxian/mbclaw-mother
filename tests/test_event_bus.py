"""Tests for MBOS EventBus — pub/sub event system."""
import pytest
from app.runtime.event_bus import EventBus
from app.runtime.event import (
    Event, RequestEvent, ExecutionStartEvent, GovernorDenyEvent, TokenLowEvent,
)


class TestEventBus:
    def setup_method(self):
        self.bus = EventBus()

    def test_subscribe_and_publish(self):
        received = []

        def handler(event):
            received.append(event)

        self.bus.subscribe(RequestEvent, handler)
        event = RequestEvent(event_id="1", session_id=42)
        self.bus.publish(event)

        assert len(received) == 1
        assert received[0].session_id == 42

    def test_multiple_subscribers(self):
        hits = []

        def h1(e):
            hits.append("h1")

        def h2(e):
            hits.append("h2")

        self.bus.subscribe(RequestEvent, h1)
        self.bus.subscribe(RequestEvent, h2)
        self.bus.publish(RequestEvent(event_id="1"))

        assert hits == ["h1", "h2"]

    def test_type_isolation(self):
        """Only subscribers for the exact event type should be called."""
        request_hits = []
        start_hits = []

        self.bus.subscribe(RequestEvent, lambda e: request_hits.append(1))
        self.bus.subscribe(ExecutionStartEvent, lambda e: start_hits.append(1))

        self.bus.publish(RequestEvent(event_id="1"))
        assert len(request_hits) == 1
        assert len(start_hits) == 0

    def test_handler_failure_isolated(self):
        """One failing handler must not affect other handlers."""
        good_hits = []

        def bad_handler(e):
            raise RuntimeError("boom")

        def good_handler(e):
            good_hits.append(1)

        self.bus.subscribe(RequestEvent, bad_handler)
        self.bus.subscribe(RequestEvent, good_handler)
        self.bus.publish(RequestEvent(event_id="1"))

        assert len(good_hits) == 1

    def test_unsubscribe(self):
        hits = []

        def handler(e):
            hits.append(1)

        self.bus.subscribe(RequestEvent, handler)
        self.bus.publish(RequestEvent(event_id="1"))
        assert len(hits) == 1

        self.bus.unsubscribe(RequestEvent, handler)
        self.bus.publish(RequestEvent(event_id="2"))
        assert len(hits) == 1  # No new hits

    def test_unsubscribe_nonexistent(self):
        """Unsubscribing a non-registered handler should not raise."""
        def handler(e):
            pass
        self.bus.unsubscribe(RequestEvent, handler)  # Should not raise

    def test_clear(self):
        hits = []

        def handler(e):
            hits.append(1)

        self.bus.subscribe(RequestEvent, handler)
        self.bus.clear()
        self.bus.publish(RequestEvent(event_id="1"))
        assert len(hits) == 0

    def test_subscriber_count(self):
        assert self.bus.subscriber_count(RequestEvent) == 0
        self.bus.subscribe(RequestEvent, lambda e: None)
        assert self.bus.subscriber_count(RequestEvent) == 1
        self.bus.subscribe(RequestEvent, lambda e: None)
        assert self.bus.subscriber_count(RequestEvent) == 2

    def test_publish_no_subscribers(self):
        """Publishing with no subscribers should not raise."""
        self.bus.publish(RequestEvent(event_id="1"))  # Should not raise

    def test_token_low_event_flow(self):
        """Simulate: TokenPool emits TOKEN_LOW → Scheduler + Governor + Audit react."""
        scheduler_hit = []
        governor_hit = []
        audit_hit = []

        self.bus.subscribe(TokenLowEvent, lambda e: scheduler_hit.append(e.provider))
        self.bus.subscribe(TokenLowEvent, lambda e: governor_hit.append(e.remaining))
        self.bus.subscribe(TokenLowEvent, lambda e: audit_hit.append(1))

        event = TokenLowEvent(event_id="1", provider="zhipu", remaining=10)
        self.bus.publish(event)

        assert scheduler_hit == ["zhipu"]
        assert governor_hit == [10]
        assert audit_hit == [1]

    def test_governor_deny_event(self):
        hits = []

        def audit(e):
            hits.append(e.rule_hit)

        self.bus.subscribe(GovernorDenyEvent, audit)
        self.bus.publish(GovernorDenyEvent(
            event_id="1", rule_hit="no_token_leak", risk_level="critical",
        ))

        assert hits == ["no_token_leak"]
