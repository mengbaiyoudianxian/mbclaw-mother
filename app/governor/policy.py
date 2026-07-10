"""MBOS Governor — policy evaluation engine.

Policy evaluates all Constitution rules against a request and
returns the first deny if any rule matches.
"""
from __future__ import annotations

import re
import logging
from typing import Optional

from .constitution import CONSTITUTION, ConstitutionRule
from .decision import GovernorDecision, RiskLevel

logger = logging.getLogger(__name__)


class Policy:
    """Evaluates Constitution rules against execution requests.

    Rules are checked in order. The first matching deny rule
    terminates evaluation and returns a deny decision.

    Usage:
        policy = Policy()
        decision = policy.evaluate("rm -rf /etc")
        # → GovernorDecision(allowed=False, reason="...", rule_hit="no_delete_system")
    """

    def evaluate(self, message: str,
                 context: Optional[dict] = None) -> GovernorDecision:
        """Evaluate all Constitution rules against a message.

        Args:
            message: The user message or command to check.
            context: Optional execution context (session_id, request_id, etc.).

        Returns:
            GovernorDecision — allowed=True if no rules match, otherwise deny.
        """
        if not message or not message.strip():
            return GovernorDecision(
                allowed=False,
                reason="消息为空",
                risk_level=RiskLevel.LOW,
                rule_hit="empty_message",
            )

        for rule in CONSTITUTION:
            try:
                if re.search(rule.pattern, message, re.IGNORECASE | re.VERBOSE):
                    logger.warning(
                        "Constitution rule '%s' triggered for message: %s...",
                        rule.name, message[:100]
                    )
                    return GovernorDecision(
                        allowed=False,
                        reason=f"[{rule.name}] {rule.description}",
                        risk_level=RiskLevel(rule.risk_level),
                        rule_hit=rule.name,
                        metadata={"matched_rule": rule.name},
                    )
            except re.error as e:
                logger.error("Invalid regex in rule '%s': %s", rule.name, e)
                continue

        return GovernorDecision(allowed=True, risk_level=RiskLevel.NONE)

    def list_rules(self) -> list[ConstitutionRule]:
        """Return all active Constitution rules."""
        return list(CONSTITUTION)
