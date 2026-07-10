"""Tests for Worker capability matching and WorkerPool."""
import pytest
from app.worker import (
    Worker, WorkerStatus, WorkerType,
    create_llm_worker, create_tool_worker, create_system_worker,
    WorkerPool,
)


class TestWorker:
    def test_llm_worker_capabilities(self):
        w = create_llm_worker("llm-1")
        assert w.type == WorkerType.LLM
        assert "reasoning" in w.capabilities
        assert "planning" in w.capabilities
        assert "chat" in w.capabilities

    def test_tool_worker_capabilities(self):
        w = create_tool_worker("tool-1")
        assert w.type == WorkerType.TOOL
        assert "shell" in w.capabilities
        assert "filesystem" in w.capabilities

    def test_system_worker_capabilities(self):
        w = create_system_worker("sys-1")
        assert w.type == WorkerType.SYSTEM
        assert "monitor" in w.capabilities
        assert "diagnostic" in w.capabilities

    def test_can_handle(self):
        w = create_llm_worker("llm-1")
        assert w.can_handle("reasoning")
        assert not w.can_handle("shell")

    def test_is_available(self):
        w = create_llm_worker("llm-1")
        assert w.is_available()

    def test_assign_and_release(self):
        w = create_llm_worker("llm-1")
        w.assign("task-1")
        assert not w.is_available()
        assert w.current_task == "task-1"
        assert w.status == WorkerStatus.BUSY

        w.release()
        assert w.is_available()
        assert w.current_task is None
        assert w.status == WorkerStatus.IDLE

    def test_custom_worker(self):
        w = Worker(
            id="custom-1",
            type=WorkerType.LLM,
            capabilities=["vision", "code"],
        )
        assert w.can_handle("vision")
        assert w.can_handle("code")
        assert not w.can_handle("shell")


class TestWorkerPool:
    def setup_method(self):
        self.pool = WorkerPool()

    def test_register_and_find(self):
        self.pool.register(create_llm_worker("llm-1"))
        worker = self.pool.find_best("reasoning")
        assert worker is not None
        assert worker.id == "llm-1"

    def test_find_best_prefers_specialized(self):
        """More specialized worker (fewer capabilities) should be preferred."""
        general = Worker(id="gen", type=WorkerType.LLM,
                         capabilities=["reasoning", "planning", "chat", "vision"])
        specialized = Worker(id="spec", type=WorkerType.LLM,
                             capabilities=["reasoning"])
        self.pool.register(general)
        self.pool.register(specialized)
        worker = self.pool.find_best("reasoning")
        assert worker.id == "spec"

    def test_find_best_busy_worker_skipped(self):
        w = create_llm_worker("llm-1")
        w.assign("task-1")
        self.pool.register(w)
        self.pool.register(create_llm_worker("llm-2"))
        worker = self.pool.find_best("reasoning")
        assert worker.id == "llm-2"

    def test_find_best_no_match(self):
        self.pool.register(create_tool_worker("tool-1"))
        worker = self.pool.find_best("reasoning")
        assert worker is None

    def test_find_all(self):
        self.pool.register(create_llm_worker("llm-1"))
        self.pool.register(create_llm_worker("llm-2"))
        self.pool.register(create_tool_worker("tool-1"))
        workers = self.pool.find_all("reasoning")
        assert len(workers) == 2

    def test_list_available(self):
        self.pool.register(create_llm_worker("llm-1"))
        w2 = create_llm_worker("llm-2")
        w2.assign("task-1")
        self.pool.register(w2)
        available = self.pool.list_available()
        assert len(available) == 1
        assert available[0].id == "llm-1"

    def test_unregister(self):
        self.pool.register(create_llm_worker("llm-1"))
        self.pool.unregister("llm-1")
        assert self.pool.get("llm-1") is None

    def test_release_all(self):
        w1 = create_llm_worker("llm-1")
        w1.assign("task-1")
        w2 = create_tool_worker("tool-1")
        w2.assign("task-2")
        self.pool.register(w1)
        self.pool.register(w2)
        self.pool.release_all()
        assert len(self.pool.list_available()) == 2
