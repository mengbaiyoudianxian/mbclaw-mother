"""MBOS Governor v1 — execution gate.

Governor is the highest control layer. It checks every execution request
before the agent loop runs. V1 implements only two deny rules:

  1. Empty message → deny
  2. Invalid session_id (< 0) → deny
  3. Everything else → allow

Governor is NOT a permission system, policy engine, or planner.
"""
from .decision import GovernorDecision


class Governor:
    """V1 execution gate — simple allow/deny decisions."""

    def check(self, ctx, message: str) -> GovernorDecision:
        """Check whether an execution request should proceed.

        Args:
            ctx: ExecutionContext with session_id, request_id, etc.
            message: The user message text.

        Returns:
            GovernorDecision with allow=True/False and a reason string.
        """
        # Rule 1: empty message (including whitespace-only)
        if not message or not message.strip():
            return GovernorDecision(allow=False, reason="消息为空")

        # Rule 2: invalid session identifier
        if ctx.session_id < 0:
            return GovernorDecision(allow=False, reason="无效会话")

        # Rule 3: default allow
        return GovernorDecision(allow=True)
