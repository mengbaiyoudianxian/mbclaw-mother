"""Token Observer — TokenPool status."""
import os, json, time
import urllib.request


class TokenObserver:
    TP_URL = os.getenv("TOKEN_POOL_URL", "http://127.0.0.1:8100")

    def collect(self) -> dict:
        result = {
            "total_tokens": -1,
            "used_tokens": -1,
            "remaining_tokens": -1,
            "providers": [],
            "models": [],
            "request_count": -1,
            "cost": -1,
            "failure_count": -1,
        }
        try:
            # Health endpoint
            req = urllib.request.Request(f"{self.TP_URL}/health", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                health = json.loads(resp.read().decode())
            result["status"] = health.get("status", "unknown")
        except Exception:
            result["status"] = "offline"
            return result

        try:
            # Models endpoint
            req = urllib.request.Request(f"{self.TP_URL}/v1/models", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                models_data = json.loads(resp.read().decode())
            models = models_data.get("data", [])
            result["models"] = [m.get("id", "?") for m in models[:10]]
        except Exception:
            pass

        try:
            # Stats endpoint
            req = urllib.request.Request(f"{self.TP_URL}/stats", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                stats = json.loads(resp.read().decode())
            result["request_count"] = stats.get("total_requests", -1)
            result["failure_count"] = stats.get("total_failures", -1)
            result["cost"] = stats.get("total_cost", -1)
            result["total_tokens"] = stats.get("total_tokens", -1)

            providers_raw = stats.get("providers", {})
            providers = []
            for name, info in providers_raw.items():
                if isinstance(info, dict):
                    providers.append({
                        "name": name,
                        "status": "online" if info.get("available", True) else "offline",
                        "remaining": info.get("remaining_tokens", -1),
                        "model": info.get("model", ""),
                    })
            result["providers"] = providers
        except Exception:
            pass

        return result
