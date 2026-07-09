"""MBOS Governor — decision types.

GovernorDecision is the unified return from Governor.check().
It tells the Runtime whether to allow or deny an execution request.
"""
from dataclasses import dataclass, field


@dataclass
class GovernorDecision:
    """Result of a Governor policy check.

    Attributes:
        allow: True if execution may proceed, False to deny.
        reason: Human-readable explanation (used as error message on deny).
        metadata: Optional diagnostic data for logging/debugging.
    """
    allow: bool
    reason: str = ""
    metadata: dict = field(default_factory=dict)
