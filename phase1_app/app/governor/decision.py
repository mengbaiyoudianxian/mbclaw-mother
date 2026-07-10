"""MBOS Governor v2 — decision types.

GovernorDecision now includes risk_level and required_action
for the layered governance architecture.

v2: Added risk_level, required_action, tool_name for tool-level decisions.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GovernorDecision:
    """Result of a Governor policy check.

    Attributes:
        allow: True if execution may proceed, False to deny.
        reason: Human-readable explanation.
        risk_level: LOW | MEDIUM | HIGH | CRITICAL
        required_action: execute | confirm | deny
        tool_name: Name of tool being evaluated (for tool-level checks)
        metadata: Optional diagnostic data.
    """
    allow: bool
    reason: str = ""
    risk_level: str = "LOW"
    required_action: str = "execute"  # execute | confirm | deny
    tool_name: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "allow": self.allow,
            "reason": self.reason,
            "risk_level": self.risk_level,
            "required_action": self.required_action,
            "tool_name": self.tool_name,
        }
