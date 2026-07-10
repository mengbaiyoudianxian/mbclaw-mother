"""MBOS Scheduler v2 — task queue + LLM dispatch.

v2: Added TaskQueue with priority, submit/schedule/dispatch.
    LLM dispatch preserved from v1.
"""
import os, time, uuid, threading, queue
import httpx
from dataclasses import dataclass, field

from app.token_pool.pool import TokenPool

TP_URL = os.getenv("TOKEN_POOL_URL", "http://127.0.0.1:8100")
TP_PROXY_KEY = os.getenv("TOKEN_POOL_PROXY_KEY", "")


@dataclass(order=True)
class Task:
    """A scheduled task with priority."""
    priority: int
    task_id: str = field(compare=False)
    task_type: str = field(compare=False, default="llm")
    payload: dict = field(default_factory=dict)
    status: str = field(compare=False, default="pending")
    created_at: float = field(compare=False, default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id, "type": self.task_type,
            "priority": self.priority, "status": self.status,
            "created_at": round(self.created_at, 1),
        }


class Scheduler:
    """V2 — task queue + LLM dispatch."""

    def __init__(self):
        self.token_pool = TokenPool()
        self._task_queue: queue.PriorityQueue = queue.PriorityQueue()
        self._tasks: dict[str, Task] = {}
        self._lock = threading.Lock()
        self._stats = {"submitted": 0, "dispatched": 0, "completed": 0, "failed": 0}

    # ── Task Queue ──────────────────────────────────────────

    def submit(self, task_type: str, payload: dict = None,
               priority: int = 5) -> Task:
        """Submit a task to the queue."""
        tid = f"{task_type}-{uuid.uuid4().hex[:8]}"
        task = Task(task_id=tid, task_type=task_type,
                    payload=payload or {}, priority=priority)
        self._task_queue.put(task)
        with self._lock:
            self._tasks[tid] = task
            self._stats["submitted"] += 1
        return task

    def schedule(self) -> list[Task]:
        """Drain the queue and return tasks in priority order."""
        tasks = []
        while not self._task_queue.empty():
            try:
                task = self._task_queue.get_nowait()
                task.status = "scheduled"
                tasks.append(task)
            except queue.Empty:
                break
        return tasks

    def dispatch_task(self, task: Task) -> dict:
        """Dispatch a single task to execution."""
        with self._lock:
            self._stats["dispatched"] += 1
            task.status = "running"
        try:
            # For now, tasks are simple dict payloads
            result = {"task_id": task.task_id, "type": task.task_type,
                     "status": "completed", "payload": task.payload}
            with self._lock:
                self._stats["completed"] += 1
                task.status = "completed"
            return result
        except Exception as e:
            with self._lock:
                self._stats["failed"] += 1
                task.status = "failed"
            return {"task_id": task.task_id, "type": task.task_type,
                   "status": "failed", "error": str(e)}

    # ── LLM Dispatch (v1 compat) ────────────────────────────

    def dispatch(self, messages: list[dict], llm_client=None) -> tuple:
        """Dispatch LLM call. Returns (raw_response: str|None, error: str)."""
        if llm_client:
            return self._call_with_client(llm_client, messages)

        candidates = self.token_pool.acquire()
        if candidates:
            return self._call_with_pool(messages, candidates)

        raw, err = self._call_with_production_tp(messages)
        if raw is not None:
            return raw, err

        from app.llm import LLMClient
        return self._call_with_client(LLMClient(), messages)

    def _call_with_client(self, llm_client, messages: list[dict]) -> tuple:
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
                json={"model": llm_client.model, "messages": messages,
                     "temperature": 0.3, "max_tokens": 2000},
                timeout=120,
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            return raw, ""
        except Exception as e:
            return None, str(e)[:60]

    def _call_with_pool(self, messages: list[dict], candidates: list) -> tuple:
        last_err = ""
        for c in candidates[:4]:
            try:
                r = httpx.post(
                    f"{c.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {c.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": c.model, "messages": messages,
                         "temperature": 0.3, "max_tokens": 600},
                    timeout=15,
                )
                if r.status_code == 200:
                    raw = r.json()["choices"][0]["message"]["content"]
                    return raw, ""
                last_err = f"{r.status_code}"
            except Exception as e:
                last_err = str(e)[:60]
        return None, last_err

    def _call_with_production_tp(self, messages: list[dict]) -> tuple:
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

    # ── Status ──────────────────────────────────────────────

    def status(self) -> dict:
        with self._lock:
            return {
                "stats": dict(self._stats),
                "pending_tasks": len(self._tasks),
                "queue_size": self._task_queue.qsize(),
            }
