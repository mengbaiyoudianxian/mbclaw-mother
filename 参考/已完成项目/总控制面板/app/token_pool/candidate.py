"""MBOS TokenPool — candidate types.

TokenCandidate represents a callable LLM resource (provider + key + model).
"""
from dataclasses import dataclass, field


@dataclass
class TokenCandidate:
    """A single LLM API resource.

    Attributes:
        provider: Provider name (e.g. 'zhipu', 'deepseek-cn').
        model: Model identifier string.
        api_key: API key for authentication.
        base_url: API endpoint base URL.
        priority: Lower values = higher priority. 0 is highest.
        metadata: Additional provider-specific data.
    """
    provider: str
    model: str
    api_key: str
    base_url: str = ""
    priority: int = 0
    metadata: dict = field(default_factory=dict)
