"""MBOS Governor — decision types for Constitution Layer.

GovernorDecision carries the result of a policy/constitution check.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class GovernorDecision:
    """Result of a Governor constitution/policy check.

    Attributes:
        allowed: True if execution may proceed, False to deny.
        reason: Human-readable explanation (used as error message on deny).
        risk_level: Assessed risk level of the operation.
        rule_hit: The constitution rule that triggered (empty if allowed).
        metadata: Optional diagnostic data for logging/debugging.
    """
    allowed: bool
    reason: str = ""
    risk_level: RiskLevel = RiskLevel.NONE
    rule_hit: str = ""
    metadata: dict = field(default_factory=dict)
