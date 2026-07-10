"""MBOS Observation Layer — unified status collection.

Architecture:
  control_plane tool → ObserverAggregator → individual observers → system state
"""
from .system_observer import SystemObserver
from .runtime_observer import RuntimeObserver
from .token_observer import TokenObserver
from .memory_observer import MemoryObserver


class ObserverAggregator:
    """Unified observation entry point for control_plane tool."""

    def __init__(self):
        self.system = SystemObserver()
        self.runtime = RuntimeObserver()
        self.token = TokenObserver()
        self.memory = MemoryObserver()

    def get_system_status(self) -> dict:
        return self.system.collect()

    def get_runtime_status(self) -> dict:
        return self.runtime.collect()

    def get_token_pool_status(self) -> dict:
        return self.token.collect()

    def get_memory_status(self) -> dict:
        return self.memory.collect()

    def get_gateway_status(self) -> dict:
        return self.runtime.gateway_status()

    def get_worker_status(self) -> dict:
        return self.runtime.worker_status()

    def full_report(self) -> dict:
        return {
            "system": self.get_system_status(),
            "runtime": self.get_runtime_status(),
            "token_pool": self.get_token_pool_status(),
            "memory": self.get_memory_status(),
            "gateway": self.get_gateway_status(),
            "workers": self.get_worker_status(),
        }
