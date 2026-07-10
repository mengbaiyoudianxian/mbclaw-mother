"""mbclaw_bridge.py — bridge old Mother API to new Phase 1 Runtime.

Production integration: QQBot → Gateway → /api/mother/run → this bridge → Phase 1 Runtime.
"""
from __future__ import annotations
import sys, os

# Ensure phase1 is importable
_phase1_path = os.path.join(os.path.dirname(__file__), "..", "phase1_app")
if _phase1_path not in sys.path:
    sys.path.insert(0, _phase1_path)

# LLM calls go through production TokenPool
os.environ.setdefault("TOKEN_POOL_URL", "http://127.0.0.1:8100")
os.environ.setdefault("MBCLAW_LLM_MOCK", "0")


def run_goal(goal: str, session_id: int = 0, max_turns: int = 5) -> dict:
    """Call Phase 1 MotherRuntime.run() and return compatible dict.

    Returns:
        {"reply": str, "success": bool, "turns": int, "tool_calls": list}
    """
    try:
        sys.path.insert(0, _phase1_path)
        from app.runtime.kernel import get_runtime
        rt = get_runtime()
        result = rt.run(goal, session_id=session_id, max_turns=max_turns)
        return {
            "reply": result.output or "（母体已处理，无文字回复）",
            "success": result.success,
            "episode_id": str(session_id),
            "turns": 1,
            "tool_calls": [],
        }
    except Exception as e:
        return {
            "reply": f"母体处理异常: {e}",
            "success": False,
            "episode_id": str(session_id),
            "turns": 0,
            "tool_calls": [],
        }
