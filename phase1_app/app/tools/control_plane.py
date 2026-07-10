"""Control Plane Tool — MBOS self-observation.

Provides read-only access to Mother runtime status.
All data comes from Observer layer, never from shell guessing.

Methods:
  get_system_status()   → CPU, memory, disk, load, processes
  get_runtime_status()  → MBOS kernel status
  get_token_pool_status() → LLM provider status
  get_gateway_status()  → Adapter/connection status
  get_memory_status()   → Memory storage status
  get_worker_status()   → Worker pool status
"""
import json
from app.observer import ObserverAggregator

_observer = ObserverAggregator()

METHODS = {
    "get_system_status":    (_observer.get_system_status,    "系统状态 (CPU/内存/磁盘/负载)"),
    "get_runtime_status":   (_observer.get_runtime_status,   "MBOS Runtime状态"),
    "get_token_pool_status":(_observer.get_token_pool_status,"TokenPool状态"),
    "get_gateway_status":   (_observer.get_gateway_status,   "Gateway状态"),
    "get_memory_status":    (_observer.get_memory_status,    "Memory状态"),
    "get_worker_status":    (_observer.get_worker_status,    "Worker状态"),
    "full_report":          (_observer.full_report,          "完整系统报告"),
}


def execute(method: str) -> str:
    """Execute a control_plane method. Returns JSON string."""
    if method not in METHODS:
        available = ", ".join(METHODS.keys())
        return json.dumps({"error": f"未知方法: {method}", "available": available},
                         ensure_ascii=False)
    try:
        fn, _ = METHODS[method]
        result = fn()
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e), "method": method}, ensure_ascii=False)
