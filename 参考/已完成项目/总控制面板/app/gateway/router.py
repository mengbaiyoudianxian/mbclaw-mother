import asyncio
from app.agent import StandardMessage
from app.runtime import get_runtime

class MessageRouter:
    def __init__(self):
        self._runtime = None

    def _ensure_runtime(self):
        if self._runtime is None:
            self._runtime = get_runtime()

    async def send_to_agent(self, msg: StandardMessage) -> str:
        self._ensure_runtime()
        try:
            result = self._runtime.run(
                message=msg.content,
                session_id=abs(hash(f"{msg.channel}:{msg.user_id}")) % 100000,
                max_turns=5,
            )
            return result.output or "收到（母体-小梦已读）"
        except Exception as e:
            return f'处理失败: {e}'

_router = MessageRouter()
def get_router() -> MessageRouter:
    return _router
