"""MBOS TokenPool HTTP Client — connect to external TokenPool service.

Provides HTTP-based model selection, quota management, and health
checks against the TokenPool service running on port 8100.

If the TokenPool service is unreachable, the client gracefully degrades
to the local ResourceManager fallback with explicit status reporting.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class TokenPoolStatus(str, Enum):
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"


@dataclass
class TokenPoolResponse:
    """Standardized response from TokenPool operations.

    Attributes:
        success: Whether the operation succeeded.
        status: Current TokenPool connection status.
        provider: Selected provider name.
        model: Selected model name.
        quota_remaining: Remaining quota for the provider.
        error: Error message if the operation failed.
        data: Additional response data.
    """
    success: bool = False
    status: TokenPoolStatus = TokenPoolStatus.OFFLINE
    provider: str = ""
    model: str = ""
    quota_remaining: int = 0
    error: str = ""
    data: dict = field(default_factory=dict)


class TokenPoolClient:
    """HTTP client for the TokenPool service (port 8100).

    Connects to the external TokenPool service for model selection
    and quota management. Falls back to the local ResourceManager
    if the service is unreachable.

    Usage:
        client = TokenPoolClient(resource_manager)
        status = client.health_check()
        response = client.select_model({"capability": "reasoning"})
    """

    def __init__(self, resource_manager=None, base_url: str = "http://127.0.0.1:8100"):
        from app.token_pool.resource_manager import ResourceManager
        self._resource_manager = resource_manager or ResourceManager()
        self._base_url = base_url
        self._connected = False
        self._last_error = ""
        self._status = TokenPoolStatus.OFFLINE
        self._connect()

    def _connect(self) -> bool:
        """Attempt to establish connection to TokenPool service.

        Returns:
            True if connection succeeded.
        """
        try:
            import urllib.request
            import json

            req = urllib.request.Request(
                f"{self._base_url}/status",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status not in (200, 201):
                    raise ConnectionError(f"TokenPool returned HTTP {resp.status}")
                data = json.loads(resp.read().decode())
                self._connected = True
                self._status = TokenPoolStatus.ONLINE
                self._last_error = ""
                logger.info("TokenPoolClient: connected to %s", self._base_url)
                return True
        except Exception as e:
            self._connected = False
            self._status = TokenPoolStatus.OFFLINE
            self._last_error = str(e)
            logger.warning(
                "TokenPoolClient: cannot connect to %s — using local fallback (%s)",
                self._base_url, e,
            )
            return False

    # ── Public interface ──────────────────────────────────────

    def health_check(self) -> TokenPoolResponse:
        """Check TokenPool service health.

        Returns:
            TokenPoolResponse with status and error details.
        """
        try:
            import urllib.request
            import json

            req = urllib.request.Request(
                f"{self._base_url}/health",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode())
                self._connected = True
                self._status = TokenPoolStatus.ONLINE
                self._last_error = ""
                return TokenPoolResponse(
                    success=True,
                    status=TokenPoolStatus.ONLINE,
                    data=data,
                )
        except Exception as e:
            self._connected = False
            self._status = TokenPoolStatus.OFFLINE
            self._last_error = str(e)
            return TokenPoolResponse(
                success=False,
                status=TokenPoolStatus.OFFLINE,
                error=f"TokenPool unreachable: {e}",
            )

    def get_status(self) -> TokenPoolResponse:
        """Get current TokenPool service status.

        Returns:
            TokenPoolResponse with connection status and provider/model info.
        """
        if not self._connected:
            # Try reconnect
            self._connect()

        try:
            import urllib.request
            import json

            req = urllib.request.Request(
                f"{self._base_url}/status",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode())
                self._connected = True
                self._status = TokenPoolStatus.ONLINE
                return TokenPoolResponse(
                    success=True,
                    status=TokenPoolStatus.ONLINE,
                    data=data,
                )
        except Exception as e:
            self._connected = False
            self._status = TokenPoolStatus.OFFLINE
            self._last_error = str(e)
            return TokenPoolResponse(
                success=False,
                status=TokenPoolStatus.OFFLINE,
                error=f"TokenPool unreachable: {e}",
                data={"providers": len(self._resource_manager.list_providers()),
                      "fallback": "local"},
            )

    def select_model(self, task_requirement: dict) -> TokenPoolResponse:
        """Select the best model for a task requirement.

        Tries the HTTP TokenPool service first. Falls back to the
        local ResourceManager if the service is unavailable.

        Args:
            task_requirement: Dict with capability, prefer_cost, prefer_latency.

        Returns:
            TokenPoolResponse with provider, model, and status.
        """
        if not self._connected:
            self._connect()

        # ── Try HTTP TokenPool ──
        if self._connected:
            try:
                import urllib.request
                import json

                body = json.dumps(task_requirement).encode()
                req = urllib.request.Request(
                    f"{self._base_url}/select_model",
                    data=body,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode())
                    return TokenPoolResponse(
                        success=True,
                        status=TokenPoolStatus.ONLINE,
                        provider=data.get("provider", ""),
                        model=data.get("model", ""),
                        quota_remaining=data.get("quota_remaining", 0),
                        data=data,
                    )
            except Exception as e:
                logger.warning("TokenPoolClient: HTTP select_model failed — %s", e)
                self._status = TokenPoolStatus.DEGRADED
                # Fall through to local fallback

        # ── Local fallback ──
        result = self._resource_manager.select_model(task_requirement)
        if result is None:
            return TokenPoolResponse(
                success=False,
                status=self._status,
                error=f"no model found for {task_requirement} (TokenPool: {self._last_error})",
            )

        provider, model = result
        return TokenPoolResponse(
            success=True,
            status=TokenPoolStatus.DEGRADED if not self._connected else TokenPoolStatus.ONLINE,
            provider=provider,
            model=model,
            data={"fallback": "local"},
        )

    def consume(self, provider: str, amount: int = 1) -> TokenPoolResponse:
        """Consume quota from a provider.

        Tries HTTP first, falls back to local ResourceManager.

        Args:
            provider: Provider name.
            amount: Amount of quota to consume.

        Returns:
            TokenPoolResponse with remaining quota.
        """
        if not self._connected:
            self._connect()

        if self._connected:
            try:
                import urllib.request
                import json

                body = json.dumps({"provider": provider, "amount": amount}).encode()
                req = urllib.request.Request(
                    f"{self._base_url}/consume",
                    data=body,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode())
                    return TokenPoolResponse(
                        success=True,
                        status=TokenPoolStatus.ONLINE,
                        provider=provider,
                        quota_remaining=data.get("remaining", 0),
                    )
            except Exception as e:
                logger.warning("TokenPoolClient: HTTP consume failed — %s", e)

        # Local fallback
        ok = self._resource_manager.consume_quota(provider, amount)
        p = self._resource_manager.get_provider(provider)
        return TokenPoolResponse(
            success=ok,
            status=TokenPoolStatus.DEGRADED if not self._connected else TokenPoolStatus.ONLINE,
            provider=provider,
            quota_remaining=p.quota_remaining if p else 0,
            data={"fallback": "local"},
        )

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def status(self) -> TokenPoolStatus:
        return self._status

    @property
    def last_error(self) -> str:
        return self._last_error
