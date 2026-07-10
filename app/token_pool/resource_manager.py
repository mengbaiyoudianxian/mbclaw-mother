"""MBOS TokenPool v2 — Resource Manager.

Manages LLM providers, models, quotas, costs, context windows,
latency profiles, and failure tracking. Provides model selection
based on task requirements.

V2 upgrades from V1:
  - Provider/Model metadata (context, cost, latency, available)
  - select_model(task_requirement) — capability-based model selection
  - Quota and failure tracking
  - Maintains backward compat with V1 acquire() interface
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Metadata for a single LLM model.

    Attributes:
        name: Model identifier (e.g., 'glm-4', 'gpt-4o').
        context: Max context window (e.g., '128K').
        cost: Relative cost indicator ('low', 'medium', 'high').
        available: Whether the model is currently reachable.
        latency: Typical latency ('fast', 'normal', 'slow').
        capabilities: Special capabilities (e.g., ['vision', 'code']).
    """
    name: str
    context: str = "8K"
    cost: str = "medium"
    available: bool = True
    latency: str = "normal"
    capabilities: list[str] = field(default_factory=list)


@dataclass
class ProviderInfo:
    """Metadata for an LLM provider with its models.

    Attributes:
        provider: Provider name (e.g., 'zhipu', 'openai', 'deepseek').
        models: Available models from this provider.
        quota_remaining: Remaining quota (requests or tokens).
    """
    provider: str
    models: list[ModelInfo] = field(default_factory=list)
    quota_remaining: int = 1000
    failure_count: int = 0


class ResourceManager:
    """V2 TokenPool — manages LLM providers as a resource pool.

    Tracks provider/model metadata and selects optimal models
    based on task requirements (capability, cost preference, etc.).

    Usage:
        rm = ResourceManager()
        rm.register_provider(ProviderInfo(
            provider="zhipu",
            models=[ModelInfo(name="glm-4v", capabilities=["vision"])],
        ))
        model = rm.select_model({"capability": "vision"})
        # → ("zhipu", "glm-4v")
    """

    def __init__(self):
        self._providers: dict[str, ProviderInfo] = {}

    def register_provider(self, provider: ProviderInfo) -> None:
        """Register a provider with its models."""
        self._providers[provider.provider] = provider
        logger.info(
            "ResourceManager: registered provider '%s' with %d model(s)",
            provider.provider, len(provider.models),
        )

    def unregister_provider(self, provider_name: str) -> None:
        """Remove a provider."""
        self._providers.pop(provider_name, None)

    def select_model(self, task_requirement: dict) -> Optional[tuple[str, str]]:
        """Select the best model for a task requirement.

        Selection criteria (in order):
          1. Capability match (e.g., 'vision', 'code')
          2. Model availability
          3. Provider quota > 0
          4. Lowest cost among matches
          5. Lowest failure count

        Args:
            task_requirement: Dict with optional keys:
                - capability: str (e.g., 'vision', 'reasoning')
                - prefer_cost: str ('low', 'medium', 'high')
                - prefer_latency: str ('fast', 'normal')

        Returns:
            Tuple of (provider_name, model_name) or None if no match.
        """
        required_capability = task_requirement.get("capability", "")
        prefer_cost = task_requirement.get("prefer_cost")
        prefer_latency = task_requirement.get("prefer_latency")

        candidates: list[tuple[ProviderInfo, ModelInfo]] = []

        for provider in self._providers.values():
            if provider.quota_remaining <= 0:
                continue

            for model in provider.models:
                if not model.available:
                    continue

                # Capability matching
                if required_capability:
                    if required_capability not in model.capabilities:
                        continue

                candidates.append((provider, model))

        if not candidates:
            logger.warning(
                "ResourceManager: no model found for capability '%s'",
                required_capability,
            )
            return None

        # ── Scoring ──────────────────────────────────────────
        cost_rank = {"low": 0, "medium": 1, "high": 2}
        latency_rank = {"fast": 0, "normal": 1, "slow": 2}

        def score(candidate: tuple[ProviderInfo, ModelInfo]) -> tuple:
            provider, model = candidate
            s_cost = cost_rank.get(model.cost, 1)
            s_latency = latency_rank.get(model.latency, 1)
            s_failures = provider.failure_count

            # Boost if matches preference
            if prefer_cost == model.cost:
                s_cost -= 0.5
            if prefer_latency == model.latency:
                s_latency -= 0.5

            return (s_cost, s_latency, s_failures)

        candidates.sort(key=score)
        best_provider, best_model = candidates[0]
        logger.info(
            "ResourceManager: selected %s/%s for capability '%s'",
            best_provider.provider, best_model.name, required_capability,
        )
        return (best_provider.provider, best_model.name)

    def record_failure(self, provider_name: str) -> None:
        """Record a provider failure for reliability tracking."""
        if provider_name in self._providers:
            self._providers[provider_name].failure_count += 1

    def record_success(self, provider_name: str) -> None:
        """Reset failure count on successful call."""
        if provider_name in self._providers:
            self._providers[provider_name].failure_count = 0

    def consume_quota(self, provider_name: str, amount: int = 1) -> bool:
        """Consume quota from a provider. Returns False if insufficient."""
        if provider_name not in self._providers:
            return False
        provider = self._providers[provider_name]
        if provider.quota_remaining < amount:
            return False
        provider.quota_remaining -= amount
        return True

    def list_providers(self) -> list[ProviderInfo]:
        """List all registered providers."""
        return list(self._providers.values())

    def get_provider(self, name: str) -> Optional[ProviderInfo]:
        """Get a specific provider by name."""
        return self._providers.get(name)
