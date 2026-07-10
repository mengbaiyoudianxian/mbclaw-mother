"""Tests for TokenPool HTTP Client — disconnect, fallback, graceful degradation."""
import pytest
from app.token_pool import ResourceManager, ProviderInfo, ModelInfo, TokenPoolClient, TokenPoolStatus


class TestTokenPoolClient:
    def setup_method(self):
        from app.state import GlobalState
        GlobalState.reset_instance()
        self.rm = ResourceManager()
        self.rm.register_provider(ProviderInfo(
            provider="zhipu",
            models=[ModelInfo(name="glm-4", capabilities=["reasoning"])],
            quota_remaining=500,
        ))

    def test_client_initializes_in_offline_mode(self):
        """Client should start OFFLINE when no TokenPool service available."""
        client = TokenPoolClient(
            resource_manager=self.rm,
            base_url="http://127.0.0.1:19999",  # non-existent port
        )
        assert not client.is_connected
        assert client.status == TokenPoolStatus.OFFLINE

    def test_select_model_falls_back_to_local(self):
        """When TokenPool is unavailable, select_model uses local fallback."""
        client = TokenPoolClient(
            resource_manager=self.rm,
            base_url="http://127.0.0.1:19999",
        )
        response = client.select_model({"capability": "reasoning"})
        assert response.success
        assert response.status == TokenPoolStatus.DEGRADED
        assert response.provider == "zhipu"
        assert response.model == "glm-4"
        assert response.data.get("fallback") == "local"

    def test_consume_falls_back_to_local(self):
        client = TokenPoolClient(
            resource_manager=self.rm,
            base_url="http://127.0.0.1:19999",
        )
        response = client.consume("zhipu", 10)
        assert response.success
        assert response.status == TokenPoolStatus.DEGRADED
        assert response.quota_remaining == 490

    def test_health_check_offline(self):
        client = TokenPoolClient(
            resource_manager=self.rm,
            base_url="http://127.0.0.1:19999",
        )
        response = client.health_check()
        assert not response.success
        assert response.status == TokenPoolStatus.OFFLINE
        assert "unreachable" in response.error.lower()

    def test_get_status_offline(self):
        client = TokenPoolClient(
            resource_manager=self.rm,
            base_url="http://127.0.0.1:19999",
        )
        response = client.get_status()
        assert not response.success
        assert response.status == TokenPoolStatus.OFFLINE
        assert response.data.get("fallback") == "local"

    def test_select_model_no_match(self):
        """When no model matches, even locally, should fail."""
        client = TokenPoolClient(
            resource_manager=self.rm,
            base_url="http://127.0.0.1:19999",
        )
        response = client.select_model({"capability": "audio_transcription"})
        assert not response.success
        assert "no model found" in response.error

    def test_client_has_last_error(self):
        client = TokenPoolClient(
            resource_manager=self.rm,
            base_url="http://127.0.0.1:19999",
        )
        assert client.last_error != ""

    def test_token_pool_status_enum_values(self):
        assert TokenPoolStatus.ONLINE.value == "online"
        assert TokenPoolStatus.DEGRADED.value == "degraded"
        assert TokenPoolStatus.OFFLINE.value == "offline"

    def test_consume_unknown_provider_fallback(self):
        client = TokenPoolClient(
            resource_manager=self.rm,
            base_url="http://127.0.0.1:19999",
        )
        response = client.consume("unknown_provider", 1)
        assert not response.success
        assert response.quota_remaining == 0
