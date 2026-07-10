"""Runtime Observer — MBOS kernel status."""
import os, time, subprocess

_START_TIME = time.time()


class RuntimeObserver:
    def collect(self) -> dict:
        pid = os.getpid()
        return {
            "version": "2.0.0-phase1",
            "uptime_seconds": round(time.time() - _START_TIME),
            "pid": pid,
            "current_phase": "phase1",
            "active_tasks": self._active_tasks(),
            "execution_engine_status": "running",
            "tool_runtime_status": self._tool_runtime_status(),
        }

    def gateway_status(self) -> dict:
        try:
            r = subprocess.run(["ss", "-lntp"], capture_output=True, text=True, timeout=3)
            ports = {}
            for line in r.stdout.split("\n"):
                if "LISTEN" not in line:
                    continue
                parts = line.split()
                for p in parts:
                    if ":" in p and p.split(":")[-1].isdigit():
                        port = int(p.split(":")[-1])
                        ports[str(port)] = True
            return {
                "adapters": ["web", "qq", "wechat"],
                "qq": ports.get("8080", False) and "connected" or "disconnected",
                "web": ports.get("8000", False) and "running" or "stopped",
                "api": ports.get("8000", False) and "running" or "stopped",
                "websocket": ports.get("8080", False) and "connected" or "disconnected",
                "connected_users": -1,  # requires adapter state tracking
            }
        except Exception:
            return {"error": "unavailable"}

    def worker_status(self) -> dict:
        return {
            "workers": ["code", "research", "memory_search", "summary"],
            "busy": 0,
            "idle": 4,
            "failed": 0,
        }

    def _active_tasks(self) -> int:
        return 0  # Single-threaded for now

    def _tool_runtime_status(self) -> str:
        return "v1.2-process-isolated"
