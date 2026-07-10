"""Memory Observer — MBOS memory storage status."""
import os, json, time


class MemoryObserver:
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")

    def collect(self) -> dict:
        result = {
            "short_memory": "active",
            "long_memory": self._long_memory_status(),
            "vector_db": "not_configured",
            "memory_count": self._memory_count(),
            "last_update": self._last_update(),
        }
        return result

    def _long_memory_status(self) -> str:
        try:
            from mother.memory import knowledge
            count = len(knowledge.list_all(limit=9999))
            return f"active ({count} entries)"
        except Exception:
            return "inactive"

    def _memory_count(self) -> int:
        count = 0
        try:
            from mother.memory import knowledge
            count += len(knowledge.list_all(limit=9999))
        except Exception:
            pass
        try:
            from mother.memory import experience
            count += experience.count()
        except Exception:
            pass
        return count

    def _last_update(self) -> str:
        try:
            kb_path = os.path.join(self.DATA_DIR, "knowledge_store.json")
            if os.path.exists(kb_path):
                mtime = os.path.getmtime(kb_path)
                return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
        except Exception:
            pass
        return "unknown"
