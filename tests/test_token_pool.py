"""Tests for TokenPool Resource Manager — model selection and provider management."""
import pytest
from app.token_pool import ResourceManager, ProviderInfo, ModelInfo


class TestResourceManager:
    def setup_method(self):
        self.rm = ResourceManager()
        self.rm.register_provider(ProviderInfo(
            provider="zhipu",
            models=[
                ModelInfo(name="glm-4", context="128K", cost="medium",
                          capabilities=["reasoning", "planning", "chat"]),
                ModelInfo(name="glm-4v", context="128K", cost="medium",
                          capabilities=["vision", "reasoning"]),
            ],
            quota_remaining=500,
        ))
        self.rm.register_provider(ProviderInfo(
            provider="deepseek",
            models=[
                ModelInfo(name="deepseek-chat", context="64K", cost="low",
                          capabilities=["reasoning", "chat"]),
                ModelInfo(name="deepseek-coder", context="64K", cost="low",
                          capabilities=["code", "reasoning"]),
            ],
            quota_remaining=500,
        ))
        self.rm.register_provider(ProviderInfo(
            provider="openai",
            models=[
                ModelInfo(name="gpt-4o", context="128K", cost="high",
                          capabilities=["vision", "reasoning", "planning", "chat"]),
            ],
            quota_remaining=100,
        ))

    def test_select_reasoning_model(self):
        result = self.rm.select_model({"capability": "reasoning"})
        assert result is not None
        provider, model = result
        assert provider in ("zhipu", "deepseek", "openai")
        assert model in ("glm-4", "deepseek-chat", "gpt-4o")

    def test_select_vision_model(self):
        result = self.rm.select_model({"capability": "vision"})
        assert result is not None
        provider, model = result
        # Only glm-4v and gpt-4o support vision
        assert model in ("glm-4v", "gpt-4o")

    def test_select_code_model(self):
        result = self.rm.select_model({"capability": "code"})
        assert result is not None
        _, model = result
        assert model == "deepseek-coder"

    def test_select_prefer_low_cost(self):
        result = self.rm.select_model({"capability": "reasoning", "prefer_cost": "low"})
        assert result is not None
        provider, _ = result
        assert provider == "deepseek"

    def test_select_unavailable_model_skipped(self):
        # Make all deepseek models unavailable
        self.rm._providers["deepseek"].models[0].available = False
        self.rm._providers["deepseek"].models[1].available = False

        result = self.rm.select_model({"capability": "reasoning"})
        assert result is not None
        provider, _ = result
        assert provider != "deepseek"

    def test_select_zero_quota_skipped(self):
        self.rm._providers["deepseek"].quota_remaining = 0
        result = self.rm.select_model({"capability": "reasoning"})
        assert result is not None
        provider, _ = result
        assert provider != "deepseek"

    def test_select_no_match(self):
        result = self.rm.select_model({"capability": "audio_transcription"})
        assert result is None

    def test_record_failure(self):
        self.rm.record_failure("zhipu")
        assert self.rm._providers["zhipu"].failure_count == 1

    def test_record_success_resets_failure(self):
        self.rm.record_failure("zhipu")
        self.rm.record_failure("zhipu")
        self.rm.record_success("zhipu")
        assert self.rm._providers["zhipu"].failure_count == 0

    def test_consume_quota(self):
        assert self.rm.consume_quota("zhipu", 10)
        assert self.rm._providers["zhipu"].quota_remaining == 490

    def test_consume_quota_insufficient(self):
        assert not self.rm.consume_quota("zhipu", 1000)

    def test_consume_quota_unknown_provider(self):
        assert not self.rm.consume_quota("unknown", 1)

    def test_failure_count_affects_selection(self):
        """Provider with high failure count should be deprioritized."""
        # Make zhipu have many failures
        self.rm._providers["zhipu"].failure_count = 100
        # deepseek should be preferred now
        result = self.rm.select_model({"capability": "reasoning"})
        assert result is not None
        provider, _ = result
        # deepseek or openai — not zhipu with 100 failures
        assert provider != "zhipu"

    def test_list_providers(self):
        providers = self.rm.list_providers()
        assert len(providers) == 3
        names = {p.provider for p in providers}
        assert names == {"zhipu", "deepseek", "openai"}

    def test_get_provider(self):
        p = self.rm.get_provider("zhipu")
        assert p is not None
        assert p.provider == "zhipu"
        assert p.quota_remaining == 500

    def test_get_unknown_provider(self):
        assert self.rm.get_provider("unknown") is None
