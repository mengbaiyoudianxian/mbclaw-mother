"""MBOS Gateway v1 — unified entry layer.

Gateway is the single entry point for all external channels.
Channels convert to StandardMessage → Gateway.handle() → MotherRuntime.run().
"""
from .protocol import StandardMessage


class Gateway:
    """V1 gateway — translates StandardMessage to Runtime calls.

    All external channels (QQ, WeChat, Feishu, Web, CLI, HTTP)
    route through Gateway.handle().

    Usage:
        gw = Gateway(runtime)
        result = gw.handle(StandardMessage(content='hello', channel='qq', session_id=1))
    """

    def __init__(self, runtime):
        self.runtime = runtime

    def handle(self, message: StandardMessage):
        """Process a StandardMessage through Runtime.

        Args:
            message: StandardMessage from any channel.

        Returns:
            ExecutionResult from MotherRuntime.run().
        """
        session_id = 1
        if message.session_id:
            try:
                session_id = int(message.session_id)
            except (ValueError, TypeError):
                session_id = 1

        return self.runtime.run(
            message.content,
            session_id=session_id,
        )

    def send(self, message) -> None:
        """Placeholder for outbound message routing (future)."""
        pass
