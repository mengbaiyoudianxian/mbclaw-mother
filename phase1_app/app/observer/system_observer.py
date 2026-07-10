"""System Observer — real server metrics (CPU, memory, disk, load, processes)."""
import os, time, subprocess


class SystemObserver:
    def collect(self) -> dict:
        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "cpu": self._cpu(),
            "memory": self._memory(),
            "disk": self._disk(),
            "load": self._load(),
            "uptime": self._uptime(),
            "process_count": self._process_count(),
        }

    def _cpu(self) -> dict:
        try:
            r = subprocess.run(["lscpu"], capture_output=True, text=True, timeout=5)
            lines = r.stdout.split("\n")
            info = {}
            for line in lines:
                if ":" in line:
                    k, v = line.split(":", 1)
                    info[k.strip()] = v.strip()
            return {
                "model": info.get("Model name", "unknown"),
                "cores": info.get("CPU(s)", "unknown"),
                "architecture": info.get("Architecture", "unknown"),
            }
        except Exception as e:
            return {"error": str(e)}

    def _memory(self) -> dict:
        try:
            r = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5)
            lines = r.stdout.strip().split("\n")
            result = {}
            for line in lines:
                parts = line.split()
                if not parts:
                    continue
                key = parts[0].rstrip(":")
                if key in ("Mem:", "Swap:"):
                    result[key.rstrip(":").lower()] = {
                        "total": parts[1] if len(parts) > 1 else "",
                        "used": parts[2] if len(parts) > 2 else "",
                        "free": parts[3] if len(parts) > 3 else "",
                        "available": parts[-1] if len(parts) > 5 else "",
                    }
            return result
        except Exception as e:
            return {"error": str(e)}

    def _disk(self) -> dict:
        try:
            r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
            lines = r.stdout.strip().split("\n")
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 6:
                    return {
                        "filesystem": parts[0],
                        "size": parts[1],
                        "used": parts[2],
                        "available": parts[3],
                        "use_pct": parts[4],
                        "mount": parts[5],
                    }
            return {"error": "unexpected df output"}
        except Exception as e:
            return {"error": str(e)}

    def _load(self) -> dict:
        try:
            with open("/proc/loadavg") as f:
                parts = f.read().strip().split()
            return {"1min": float(parts[0]), "5min": float(parts[1]),
                    "15min": float(parts[2])}
        except Exception:
            return {"error": "unavailable"}

    def _uptime(self) -> str:
        try:
            with open("/proc/uptime") as f:
                uptime_s = float(f.read().split()[0])
            days = int(uptime_s // 86400)
            hours = int((uptime_s % 86400) // 3600)
            mins = int((uptime_s % 3600) // 60)
            return f"{days}d {hours}h {mins}m"
        except Exception:
            return "unknown"

    def _process_count(self) -> int:
        try:
            return len(os.listdir("/proc")) - sum(
                1 for p in os.listdir("/proc") if not p.isdigit())
        except Exception:
            return -1
