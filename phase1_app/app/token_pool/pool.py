"""MBOS TokenPool v2 — LLM resource pool with scoring.

v2: Added score-based candidate selection, provider status, quota tracking.
"""
from .candidate import TokenCandidate


class TokenPool:
    """V2 LLM resource pool with scoring.

    Usage:
        pool = TokenPool()
        pool.register(TokenCandidate(provider='zhipu', model='glm-4', api_key='...'))
        scored = pool.acquire_scored()  # sorted by score
        candidates = pool.acquire()     # v1 compat: sorted by priority
    """

    def __init__(self):
        self._tokens: list[TokenCandidate] = []

    def register(self, candidate: TokenCandidate) -> None:
        self._tokens.append(candidate)

    def acquire(self) -> list[TokenCandidate]:
        """V1 compat: return candidates sorted by priority."""
        return sorted(self._tokens, key=lambda x: x.priority)

    def acquire_scored(self) -> list[TokenCandidate]:
        """V2: return candidates sorted by weighted score (highest first)."""
        return sorted(self._tokens, key=lambda x: x.score(), reverse=True)

    def get_providers(self) -> list[dict]:
        """Return provider status summaries."""
        return [c.to_dict() for c in self._tokens]

    def status(self) -> dict:
        scored = self.acquire_scored()
        return {
            "total_candidates": len(self._tokens),
            "available": sum(1 for c in self._tokens if c.available),
            "total_quota": sum(c.quota_total for c in self._tokens),
            "total_used": sum(c.quota_used for c in self._tokens),
            "providers": [{
                "name": c.provider, "model": c.model,
                "available": c.available,
                "remaining": c.quota_remaining,
                "score": round(c.score(), 2),
            } for c in scored],
        }
