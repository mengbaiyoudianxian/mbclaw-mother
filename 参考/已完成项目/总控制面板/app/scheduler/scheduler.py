"""MBOS Scheduler v1 — LLM dispatch.

Scheduler is the only module that makes LLM HTTP calls.
Runtime calls Scheduler.dispatch() instead of httpx directly.

TokenPool provides candidates via self.token_pool.acquire().
Supports MBCLAW_LLM_MOCK=1 for testing without real API keys.
"""
import os
import httpx

from app.token_pool.pool import TokenPool


class Scheduler:
    """V1 LLM dispatch — two code paths, one interface.

    agent_run path: uses injected LLMClient.
    Gateway path: uses TokenPool candidates with failover.
    """

    def __init__(self):
        self.token_pool = TokenPool()

    def dispatch(self, messages: list[dict], llm_client=None) -> tuple:
        """Dispatch LLM call. Returns (raw_response: str|None, error: str)."""
        if llm_client:
            return self._call_with_client(llm_client, messages)
        else:
            candidates = self.token_pool.acquire()
            if candidates:
                return self._call_with_pool(messages, candidates)
            # Fallback: TokenPool empty → create LLMClient from env
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
