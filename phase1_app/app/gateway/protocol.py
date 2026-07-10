"""MBOS Gateway — unified message protocol.

StandardMessage is the canonical cross-channel message format.
Migrated from app/agent.py (Task 20).
"""
from dataclasses import dataclass, field


@dataclass
class StandardMessage:
    """Cross-channel unified message.

    All external channels (QQ, WeChat, Feishu, Web, CLI, HTTP)
    convert their messages to this format before entering Gateway.

    Attributes:
        role: Message role ('user', 'assistant', 'system').
        content: Message text content.
        channel: Source channel identifier ('qq', 'wechat', 'web', etc.).
        user_id: External user identifier.
        user_name: Display name.
        session_id: Session identifier string.
        timestamp: Unix timestamp of original message.
        metadata: Channel-specific extra data.
    """
    role: str = 'user'
    content: str = ''
    channel: str = 'unknown'
    user_id: str = ''
    user_name: str = ''
    session_id: str = ''
    timestamp: float = 0.0
    metadata: dict = field(default_factory=dict)
