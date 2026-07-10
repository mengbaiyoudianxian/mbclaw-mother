"""MBOS TokenPool v2 — candidate types with scoring.

TokenCandidate represents a callable LLM resource (provider + key + model).
v2: Added quota, cost, speed fields for scoring.
"""
from dataclasses import dataclass, field


@dataclass
class TokenCandidate:
    """A single LLM API resource with quota/cost/speed for scoring.

    Attributes:
        provider: Provider name (e.g. 'zhipu', 'deepseek-cn').
        model: Model identifier string.
        api_key: API key for authentication.
        base_url: API endpoint base URL.
        priority: Lower values = higher priority. 0 is highest.
        quota_total: Total token quota available.
        quota_used: Tokens used so far.
        cost_per_1k: Cost per 1000 tokens (USD).
        avg_latency_ms: Average response latency.
        available: Whether this candidate is currently usable.
        metadata: Additional provider-specific data.
    """
    provider: str
    model: str
    api_key: str
    base_url: str = ""
    priority: int = 0
    quota_total: int = 100000
    quota_used: int = 0
    cost_per_1k: float = 0.0
    avg_latency_ms: float = 500.0
    available: bool = True
    metadata: dict = field(default_factory=dict)

    @property
    def quota_remaining(self) -> int:
        return max(0, self.quota_total - self.quota_used)

    def score(self) -> float:
        """Compute a weighted score: availability + low cost + speed.

        Higher score = better choice.
        """
        if not self.available or self.quota_remaining <= 0:
            return -1.0
        availability = 1.0 if self.available else 0.0
        cost_score = 10.0 / (1.0 + self.cost_per_1k)
        speed_score = 1000.0 / (1.0 + self.avg_latency_ms)
        quota_score = min(self.quota_remaining / 10000.0, 10.0)
        return availability * 100 + cost_score * 5 + speed_score * 2 + quota_score

    def to_dict(self) -> dict:
        return {
            "provider": self.provider, "model": self.model,
            "available": self.available,
            "quota_remaining": self.quota_remaining,
            "quota_total": self.quota_total,
            "cost_per_1k": self.cost_per_1k,
            "avg_latency_ms": self.avg_latency_ms,
            "score": round(self.score(), 2),
        }
