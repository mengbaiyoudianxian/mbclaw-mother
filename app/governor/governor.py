"""MBOS Governor v2 — Constitution Layer.

Governor is the highest control layer in MBOS. It enforces the
Constitution through Policy evaluation before any execution proceeds.

V2 upgrades:
  - Constitution with 5 safety rules (token leak, system files, security,
    permission bypass, critical auto-deny)
  - Policy engine for rule evaluation
  - Risk-level assessment
  - Maintains backward compatibility with Governor v1 interface
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .decision import GovernorDecision, RiskLevel
from .policy import Policy

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """Minimal execution context for Governor checks.

    Attributes:
        session_id: Session identifier.
        request_id: Unique request identifier.
    """
    session_id: int = 0
    request_id: str = ""


class Governor:
    """V2 Constitution Layer — safety gate with policy enforcement.

    Evaluates every execution request against the MBOS Constitution.
    CRITICAL risk operations are auto-denied. Other rule violations
    return deny decisions with the matching rule name and reason.

    Usage:
        gov = Governor()
        ctx = ExecutionContext(session_id=1, request_id="abc")
        decision = gov.check(ctx, "rm -rf /etc")
        if not decision.allowed:
            print(f"Blocked: {decision.reason}")
    """

    def __init__(self):
        self._policy = Policy()

    def check(self, ctx: ExecutionContext,
              message: str) -> GovernorDecision:
        """Check whether an execution request should proceed.

        Evaluates input validity rules first, then Constitution rules.

        Args:
            ctx: ExecutionContext with session_id, request_id.
            message: The user message or command to evaluate.

        Returns:
            GovernorDecision with allow=True/False and reason.
        """
        # ── Input validity checks (V1 compat) ──
        if not message or not message.strip():
            return GovernorDecision(
                allowed=False,
                reason="消息为空",
                risk_level=RiskLevel.LOW,
                rule_hit="empty_message",
            )

        if ctx.session_id < 0:
            return GovernorDecision(
                allowed=False,
                reason="无效会话",
                risk_level=RiskLevel.LOW,
                rule_hit="invalid_session",
            )

        # ── Constitution evaluation ──
        context = {
            "session_id": ctx.session_id,
            "request_id": ctx.request_id,
        }
        decision = self._policy.evaluate(message, context)

        if not decision.allowed:
            logger.warning(
                "Governor DENY [%s] session=%s risk=%s: %s",
                decision.rule_hit, ctx.session_id,
                decision.risk_level.value, decision.reason,
            )

        return decision

    def list_rules(self) -> list:
        """List all active Constitution rules."""
        return self._policy.list_rules()
