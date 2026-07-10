"""MBOS Gateway — interface protocol.

GatewayProtocol defines the contract for Gateway implementations.
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class GatewayProtocol(Protocol):
    """Receive and send messages through a channel."""

    def handle(self, message) -> object:
        ...

    def send(self, message) -> None:
        ...
