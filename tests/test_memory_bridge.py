"""Tests for Memory Bridge — audit extraction and memory store."""
import pytest
from app.memory_bridge import (
    MemoryBridge, MemoryStore, MemoryExtractor, MemoryEntry,
)


class TestMemoryExtractor:
    def setup_method(self):
        self.extractor = MemoryExtractor()

    def test_extract_governor_deny(self):
        audit = ["[governor.deny] session=1 task= rule=no_token_leak"]
        entries = self.extractor.extract_from_audit(audit, "test goal")
        assert len(entries) == 1
        assert entries[0].entry_type == "decision"
        assert entries[0].rule_hit == "no_token_leak"
        assert "test goal" in entries[0].goal

    def test_extract_failure(self):
        audit = ["[execution.failed] session=1 task= error=something broke"]
        entries = self.extractor.extract_from_audit(audit, "fail goal")
        assert len(entries) == 1
        assert entries[0].entry_type == "failure"
        assert "something broke" in entries[0].error

    def test_extract_success(self):
        audit = ["[execution.finish] session=1 task="]
        entries = self.extractor.extract_from_audit(audit, "success goal")
        assert len(entries) == 1
        assert entries[0].entry_type == "success"

    def test_extract_experience(self):
        audit = ["[planner.complete] session=1 task="]
        entries = self.extractor.extract_from_audit(audit, "plan goal")
        assert len(entries) == 1
        assert entries[0].entry_type == "experience"

    def test_extract_multiple(self):
        audit = [
            "[planner.complete] session=1 task=",
            "[execution.finish] session=1 task=",
        ]
        entries = self.extractor.extract_from_audit(audit, "multi")
        assert len(entries) == 2


class TestMemoryStore:
    def setup_method(self):
        self.store = MemoryStore(max_entries=100)

    def test_store_and_query(self):
        self.store.store(MemoryEntry(entry_type="failure", goal="g1",
                                     summary="test failure"))
        results = self.store.query("failure")
        assert len(results) == 1
        assert results[0].summary == "test failure"

    def test_query_by_type(self):
        self.store.store(MemoryEntry(entry_type="failure", goal="g1"))
        self.store.store(MemoryEntry(entry_type="success", goal="g2"))
        assert len(self.store.query("failure")) == 1
        assert len(self.store.query("success")) == 1
        assert len(self.store.query()) == 2

    def test_query_by_goal(self):
        self.store.store(MemoryEntry(entry_type="success", goal="检查服务器"))
        self.store.store(MemoryEntry(entry_type="success", goal="部署项目"))
        results = self.store.query_by_goal("服务器")
        assert len(results) == 1

    def test_recent_failures(self):
        for i in range(5):
            self.store.store(MemoryEntry(entry_type="failure", goal=f"g{i}"))
        assert len(self.store.recent_failures()) == 5

    def test_recent_successes(self):
        self.store.store(MemoryEntry(entry_type="success", goal="g1"))
        assert len(self.store.recent_successes()) == 1

    def test_recent_decisions(self):
        self.store.store(MemoryEntry(entry_type="decision", rule_hit="no_token_leak"))
        assert len(self.store.recent_decisions()) == 1
        assert self.store.recent_decisions()[0].rule_hit == "no_token_leak"

    def test_max_entries(self):
        store = MemoryStore(max_entries=5)
        for i in range(10):
            store.store(MemoryEntry(entry_type="success", goal=f"g{i}"))
        assert store.size() == 5

    def test_clear(self):
        self.store.store(MemoryEntry(entry_type="success", goal="g1"))
        self.store.clear()
        assert self.store.size() == 0

    def test_store_many(self):
        entries = [
            MemoryEntry(entry_type="success", goal="a"),
            MemoryEntry(entry_type="failure", goal="b"),
        ]
        self.store.store_many(entries)
        assert self.store.size() == 2

    def test_memory_entry_fields(self):
        e = MemoryEntry(
            entry_type="decision",
            goal="test",
            summary="blocked",
            rule_hit="rule1",
            error="",
            metadata={"key": "val"},
        )
        assert e.entry_type == "decision"
        assert e.rule_hit == "rule1"
        assert e.metadata["key"] == "val"


class TestMemoryBridge:
    def setup_method(self):
        from app.runtime.event_bus import EventBus
        self.bus = EventBus()
        self.store = MemoryStore()
        self.bridge = MemoryBridge(event_bus=self.bus,
                                   memory_store=self.store)

    def test_memory_bridge_initialized(self):
        assert self.bridge.memory_store is self.store

    def test_process_audit_log(self):
        audit = [
            "[governor.deny] session=1 task= rule=no_token_leak",
            "[execution.failed] session=2 task= error=crash",
        ]
        entries = self.bridge.process_audit_log(audit, "test goal")
        assert len(entries) == 2
        assert self.store.size() == 2

    def test_on_governor_deny(self):
        from app.runtime.event import GovernorDenyEvent
        self.bridge._active_goal = "dangerous request"
        event = GovernorDenyEvent(event_id="1", rule_hit="no_delete_system",
                                  risk_level="critical")
        self.bridge._on_governor_deny(event)
        assert self.store.size() == 1
        mem = self.store.query("decision")[0]
        assert mem.rule_hit == "no_delete_system"

    def test_on_failure(self):
        from app.runtime.event import ExecutionFailedEvent
        self.bridge._active_goal = "buggy request"
        event = ExecutionFailedEvent(event_id="1", error="null pointer")
        self.bridge._on_failure(event)
        assert self.store.size() == 1
        mem = self.store.query("failure")[0]
        assert mem.error == "null pointer"
