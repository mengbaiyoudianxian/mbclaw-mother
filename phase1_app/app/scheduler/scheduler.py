"""MBOS Scheduler v1 — LLM dispatch.

Scheduler is the only module that makes LLM HTTP calls.
Runtime calls Scheduler.dispatch() instead of httpx directly.

TokenPool provides candidates via self.token_pool.acquire().
Production TokenPool HTTP at TOKEN_POOL_URL (default :8100).
Supports MBCLAW_LLM_MOCK=1 for testing without real API keys.
"""
import os
import httpx

from app.token_pool.pool import TokenPool

TP_URL = os.getenv("TOKEN_POOL_URL", "http://127.0.0.1:8100")
TP_PROXY_KEY = os.getenv("TOKEN_POOL_PROXY_KEY", "")


class Scheduler:
    """V1 LLM dispatch — three-tier: local pool → production TP → env fallback."""

    def __init__(self):
        self.token_pool = TokenPool()

    def dispatch(self, messages: list[dict], llm_client=None) -> tuple:
        """Dispatch LLM call. Returns (raw_response: str|None, error: str)."""
        if llm_client:
            return self._call_with_client(llm_client, messages)

        # Tier 1: Local TokenPool (Phase 2 will populate)
        candidates = self.token_pool.acquire()
        if candidates:
            return self._call_with_pool(messages, candidates)

        # Tier 2: Production TokenPool HTTP proxy
        raw, err = self._call_with_production_tp(messages)
        if raw is not None:
            return raw, err

        # Tier 3: LLMClient from env (last resort)
        from app.llm import LLMClient
        return self._call_with_client(LLMClient(), messages)

    # ── agent_run path ──────────────────────────────────────
    def _call_with_client(self, llm_client, messages: list[dict]) -> tuple:
        """LLM via injected LLMClient or env-based fallback."""
        if os.getenv("MBCLAW_LLM_MOCK") == "1":
            user_msg = messages[-1].get("content", "") if messages else ""
            return f"[MOCK] 收到: {user_msg[:100]}", ""
        try:
            resp = httpx.post(
                f"{llm_client.base_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    **({"Authorization": f"Bearer {llm_client.api_key}"}
                       if llm_client.api_key else {}),
                },
                json={
                    "model": llm_client.model,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 2000,
                },
                timeout=120,
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            return raw, ""
        except Exception as e:
            return None, str(e)[:60]

    # ── Gateway path ────────────────────────────────────────
    def _call_with_pool(self, messages: list[dict],
                        candidates: list) -> tuple:
        """LLM via TokenPool candidates (Gateway compat path)."""
        last_err = ""
        for c in candidates[:4]:
            try:
                r = httpx.post(
                    f"{c.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {c.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": c.model,
                        "messages": messages,
                        "temperature": 0.3,
                        "max_tokens": 600,
                    },
                    timeout=15,
                )
                if r.status_code == 200:
                    raw = r.json()["choices"][0]["message"]["content"]
                    return raw, ""
                last_err = f"{r.status_code}"
            except Exception as e:
                last_err = str(e)[:60]
        return None, last_err

    # ── Production TokenPool HTTP ───────────────────────────
    def _call_with_production_tp(self, messages: list[dict]) -> tuple:
        """Call production TokenPool at TOKEN_POOL_URL/v1/chat/completions.

        Returns (content: str|None, error: str).
        """
        if os.getenv("MBCLAW_LLM_MOCK") == "1":
            return None, "mock mode"
        headers = {"Content-Type": "application/json"}
        if TP_PROXY_KEY:
            headers["Authorization"] = f"Bearer {TP_PROXY_KEY}"
        try:
            resp = httpx.post(
                f"{TP_URL}/v1/chat/completions",
                headers=headers,
                json={"messages": messages, "max_tokens": 2000, "temperature": 0.3},
                timeout=120,
            )
            resp.raise_for_status()
            body = resp.json()
            choice = body.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            return content, ""
        except Exception as e:
            return None, str(e)[:80]
