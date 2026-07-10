"""MBOS Memory Bridge — Audit → Memory persistence pipeline.

Captures pipeline events (decisions, successes, failures, experiences)
and stores them in a structured memory store for Planner retrieval.
"""
from __future__ import annotations

import copy
import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single memory record.

    Attributes:
        entry_type: Category: decision, experience, failure, success.
        goal: The goal/request that generated this memory.
        summary: Human-readable summary.
        rule_hit: Governor rule that triggered (if decision entry).
        error: Error message (if failure entry).
        metadata: Extra context.
        timestamp: When the memory was created.
    """
    entry_type: str  # decision, experience, failure, success
    goal: str = ""
    summary: str = ""
    rule_hit: str = ""
    error: str = ""
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryExtractor:
    """Extracts structured memories from pipeline audit events.

    Converts raw event data into MemoryEntry objects categorized as:
      - decision: Governor deny decisions (what was blocked, why)
      - failure: Execution failures and errors
      - success: Completed executions
      - experience: General pipeline experiences
    """

    @staticmethod
    def extract_from_audit(audit_log: list[str], goal: str = "") -> list[MemoryEntry]:
        """Extract memories from a list of audit log entries.

        Args:
            audit_log: List of audit string entries.
            goal: The original goal/message for context.

        Returns:
            List of MemoryEntry objects.
        """
        entries: list[MemoryEntry] = []

        for entry in audit_log:
            # Governor deny
            if "governor.deny" in entry:
                rule = ""
                if "rule=" in entry:
                    rule = entry.split("rule=")[-1].strip()
                entries.append(MemoryEntry(
                    entry_type="decision",
                    goal=goal,
                    summary=f"Governor blocked: {rule}",
                    rule_hit=rule,
                    metadata={"raw": entry},
                ))

            # Execution failed
            elif "execution.failed" in entry:
                error = ""
                if "error=" in entry:
                    error = entry.split("error=", 1)[-1].strip()
                entries.append(MemoryEntry(
                    entry_type="failure",
                    goal=goal,
                    summary=f"Execution failed: {error}",
                    error=error,
                    metadata={"raw": entry},
                ))

            # Planner complete
            elif "planner.complete" in entry:
                entries.append(MemoryEntry(
                    entry_type="experience",
                    goal=goal,
                    summary="Planner successfully decomposed goal",
                    metadata={"raw": entry},
                ))

            # Execution finish
            elif "execution.finish" in entry:
                entries.append(MemoryEntry(
                    entry_type="success",
                    goal=goal,
                    summary="Execution completed successfully",
                    metadata={"raw": entry},
                ))

        return entries


class MemoryStore:
    """Thread-safe in-memory store for pipeline memories.

    Stores the most recent N memories with retrieval by type.
    """

    def __init__(self, max_entries: int = 1000):
        self._lock = threading.RLock()
        self._entries: deque[MemoryEntry] = deque(maxlen=max_entries)
        self._max_entries = max_entries

    def store(self, entry: MemoryEntry) -> None:
        """Store a memory entry."""
        with self._lock:
            self._entries.append(copy.deepcopy(entry))
            logger.debug("MemoryStore: stored %s — %s", entry.entry_type, entry.summary)

    def store_many(self, entries: list[MemoryEntry]) -> None:
        """Store multiple memory entries."""
        with self._lock:
            for entry in entries:
                self._entries.append(copy.deepcopy(entry))

    def query(self, entry_type: Optional[str] = None,
              limit: int = 50) -> list[MemoryEntry]:
        """Query memories, optionally filtered by type.

        Args:
            entry_type: Filter by memory type (decision, failure, success, experience).
            limit: Maximum entries to return.

        Returns:
            List of MemoryEntry matching the query, newest first.
        """
        with self._lock:
            if entry_type:
                filtered = [e for e in self._entries if e.entry_type == entry_type]
            else:
                filtered = list(self._entries)
            return list(reversed(filtered))[:limit]

    def query_by_goal(self, goal: str, limit: int = 50) -> list[MemoryEntry]:
        """Query memories related to a specific goal."""
        with self._lock:
            filtered = [e for e in self._entries if goal in e.goal]
            return list(reversed(filtered))[:limit]

    def recent_failures(self, limit: int = 10) -> list[MemoryEntry]:
        """Get recent failure memories for Planner context."""
        return self.query("failure", limit)

    def recent_decisions(self, limit: int = 10) -> list[MemoryEntry]:
        """Get recent Governor decisions for pattern recognition."""
        return self.query("decision", limit)

    def recent_successes(self, limit: int = 10) -> list[MemoryEntry]:
        """Get recent successes for Planner confidence."""
        return self.query("success", limit)

    def size(self) -> int:
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


class MemoryBridge:
    """Bridge between MBOS pipeline and Memory persistence.

    Subscribes to EventBus and automatically extracts memories
    from audit events, storing them in MemoryStore.

    Usage:
        bridge = MemoryBridge(kernel.event_bus, memory_store)
        # Pipeline runs → memories auto-extracted and stored
        memories = bridge.memory_store.query("failure", limit=5)
    """

    def __init__(self, event_bus=None, memory_store: Optional[MemoryStore] = None):
        from app.runtime.event_bus import EventBus
        self._event_bus = event_bus or EventBus()
        self.memory_store = memory_store or MemoryStore()
        self._extractor = MemoryExtractor()
        self._audit_buffer: list[str] = []
        self._active_goal = ""

        # Subscribe to all relevant events
        if self._event_bus:
            from app.runtime.event import (
                RequestEvent, GovernorDenyEvent, ExecutionFailedEvent,
                PlannerCompleteEvent, ExecutionFinishEvent,
            )
            self._event_bus.subscribe(RequestEvent, self._on_request)
            self._event_bus.subscribe(GovernorDenyEvent, self._on_governor_deny)
            self._event_bus.subscribe(ExecutionFailedEvent, self._on_failure)
            self._event_bus.subscribe(PlannerCompleteEvent, self._on_planner_complete)
            self._event_bus.subscribe(ExecutionFinishEvent, self._on_execution_finish)

    def _on_request(self, event) -> None:
        self._active_goal = event.payload.get("message", "")

    def _on_governor_deny(self, event) -> None:
        entry = MemoryEntry(
            entry_type="decision",
            goal=self._active_goal,
            summary=f"Governor blocked: {event.rule_hit}",
            rule_hit=event.rule_hit,
            metadata={"risk_level": event.risk_level},
        )
        self.memory_store.store(entry)

    def _on_failure(self, event) -> None:
        entry = MemoryEntry(
            entry_type="failure",
            goal=self._active_goal,
            summary=f"Execution failed: {event.error}",
            error=event.error,
        )
        self.memory_store.store(entry)

    def _on_planner_complete(self, event) -> None:
        entry = MemoryEntry(
            entry_type="experience",
            goal=self._active_goal,
            summary=f"Planned {event.task_count} tasks for: {event.goal}",
            metadata={"task_count": event.task_count, "goal": event.goal},
        )
        self.memory_store.store(entry)

    def _on_execution_finish(self, event) -> None:
        entry = MemoryEntry(
            entry_type="success",
            goal=self._active_goal,
            summary=f"Execution complete — goal: {self._active_goal}",
            metadata=event.payload,
        )
        self.memory_store.store(entry)

    def process_audit_log(self, audit_log: list[str], goal: str) -> list[MemoryEntry]:
        """Process a raw audit log and store extracted memories.

        Args:
            audit_log: List of audit string entries.
            goal: The original goal/message.

        Returns:
            List of extracted MemoryEntry objects.
        """
        entries = self._extractor.extract_from_audit(audit_log, goal)
        self.memory_store.store_many(entries)
        return entries
