"""MBOS TokenPool v1 — LLM resource pool.

TokenPool manages LLM provider/key/model candidates.
It provides a sorted candidate list to Scheduler for LLM dispatch.

V1: in-memory only. No database, no config system.
"""
from .candidate import TokenCandidate


class TokenPool:
    """V1 in-memory LLM resource pool.

    Usage:
        pool = TokenPool()
        pool.register(TokenCandidate(provider='zhipu', model='glm-4', api_key='...'))
        candidates = pool.acquire()  # sorted by priority
    """

    def __init__(self):
        self._tokens: list[TokenCandidate] = []

    def register(self, candidate: TokenCandidate) -> None:
        """Add a candidate to the pool."""
        self._tokens.append(candidate)

    def acquire(self) -> list[TokenCandidate]:
        """Return all candidates sorted by priority (lowest first)."""
        return sorted(self._tokens, key=lambda x: x.priority)
