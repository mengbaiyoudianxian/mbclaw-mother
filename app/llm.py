"""MBOS LLM Client — OpenAI-compatible chat-completions.

Restored from v0.1 (参考/已完成项目/总控制面板/app/llm.py).
Minimal — only chat(), no summarization.
"""
from __future__ import annotations

import os

import httpx


class LLMClient:
    """OpenAI-compatible chat-completions client.

    Reads credentials from env vars unless explicitly passed.
    Falls back to defaults when env is unset.
    Supports MBCLAW_LLM_MOCK=1 for testing without real API keys.
    """

    def __init__(self, base_url: str | None = None,
                 api_key: str | None = None, model: str | None = None):
        self.base_url = (base_url or os.getenv("MBCLAW_LLM_BASE_URL", "")).rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("MBCLAW_LLM_API_KEY", "")
        self.model = model or os.getenv("MBCLAW_LLM_MODEL", "")
        self._mock = os.getenv("MBCLAW_LLM_MOCK") == "1"
        # ── TokenPool proxy fallback (restored from v0.1) ──
        # If no env vars, use the local TokenPool proxy at port 8100.
        # TokenPool handles key routing, quotas, and failover internally.
        if not self.api_key and not self.base_url:
            self.base_url = "http://127.0.0.1:8100/v1"
            self.api_key = ""  # TokenPool proxy doesn't require auth key
        elif not self.base_url:
            self.base_url = "https://api.openai.com/v1"
        if not self.model:
            self.model = "gpt-4o-mini"

    def chat(self, messages: list[dict], model: str = "") -> str:
        """Simple chat interface — for QQ Bot / Gateway.

        Args:
            messages: List of {"role": "...", "content": "..."} dicts.
            model: Optional model override.

        Returns:
            LLM response text, or error string on failure.
        """
        if self._mock:
            user_msg = messages[-1].get("content", "") if messages else ""
            return f"[MOCK] 收到: {user_msg[:100]}"

        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {
            "model": model or self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
        }
        try:
            resp = httpx.post(url, headers=headers, json=body, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[LLM错误] {e}"
