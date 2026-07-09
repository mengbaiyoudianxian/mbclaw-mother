"""MBOS Context — working memory.

WorkingMemory holds per-session conversation context.
Migrated from runtime/kernel.py (Task 16).
"""
import time


class WorkingMemory:
    """In-memory context for one session. Auto-compresses at 80% token limit."""

    COMPRESS_THRESHOLD = 0.80

    def __init__(self, token_limit=6000):
        self.limit = token_limit
        self.system = ""
        self.messages: list[dict] = []  # {role, content, ts}
        self.recall = ""
        self._compress_count = 0

    def set_system(self, text: str):
        self.system = text

    def add(self, role: str, content: str):
        self.messages.append({"role": role, "content": content, "ts": time.time()})
        self._maybe_compress()

    def set_recall(self, texts: list[str]):
        if not texts:
            self.recall = ""
            return
        self.recall = "相关记忆：\n" + "\n".join(f"- {t[:200]}" for t in texts[:3])

    def to_messages(self) -> list[dict]:
        out = [{"role": "system", "content": self.system}]
        if self.recall:
            out.append({"role": "system", "content": self.recall})
        for m in self.messages[-20:]:
            out.append({"role": m["role"], "content": m["content"]})
        return out

    def total_tokens(self) -> int:
        n = len(self.system) // 4
        for m in self.messages:
            n += len(str(m.get("content", ""))) // 4
        n += len(self.recall) // 4
        return n

    def _maybe_compress(self):
        if self.total_tokens() < self.limit * self.COMPRESS_THRESHOLD:
            return
        if len(self.messages) < 4:
            return
        half = len(self.messages) // 2
        old = self.messages[:half]
        self.messages = self.messages[half:]
        summary = " | ".join(str(m.get("content", ""))[:80] for m in old[-3:])
        self.messages.insert(0, {"role": "system",
            "content": f"[历史摘要 #{self._compress_count}] {summary}",
            "ts": time.time()})
        self._compress_count += 1
