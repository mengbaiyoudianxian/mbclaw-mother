"""MBOS Governor — interface protocol.

GovernorProtocol defines the contract for Governor implementations.
Migrated from runtime/interfaces.py (Task 13).
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class GovernorProtocol(Protocol):
    """Policy check per execution request.

    check(ctx, message) → GovernorDecision.
    Must return a GovernorDecision — never raise exceptions.
    """

    def check(self, ctx, message: str):
        ...
