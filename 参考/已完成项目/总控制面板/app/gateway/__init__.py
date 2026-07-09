"""MBOS Gateway v1 — unified channel entry layer.

Gateway is the single entry point. All external channels convert to
StandardMessage and route through Gateway.handle() → MotherRuntime.run().

Legacy v6 gateway registry preserved for backward compat.
"""
from .gateway import Gateway
from .protocol import StandardMessage
from .interfaces import GatewayProtocol

# Legacy v6 exports (preserved)
from .normalize import MessageNormalizer
from .router import MessageRouter
from .dispatcher import ResponseDispatcher

class GatewayRegistry:
    adapters: dict = {}

    def register(self, name: str, adapter):
        self.adapters[name] = adapter

    def unregister(self, name: str):
        self.adapters.pop(name, None)

    def get(self, name: str):
        return self.adapters.get(name)

    def list_channels(self) -> list:
        return list(self.adapters.keys())

    async def start_all(self) -> None:
        for name, adp in self.adapters.items():
            try: await adp.start()
            except Exception as e: print(f'[gateway] {name} start failed: {e}')

    async def stop_all(self) -> None:
        for name, adp in self.adapters.items():
            try: await adp.stop()
            except Exception as e: print(f'[gateway] {name} stop failed: {e}')

_registry = GatewayRegistry()
def get_registry() -> GatewayRegistry:
    return _registry

__all__ = [
    "Gateway", "StandardMessage", "GatewayProtocol",
    "GatewayRegistry", "get_registry",
    "MessageNormalizer", "MessageRouter", "ResponseDispatcher",
]
