"""MBOS Governor v2 — execution gate with risk evaluation.

Governor is the highest control layer. It checks every execution request
and every tool call before the agent loop runs.

v2: Added evaluate() for tool-level risk assessment with registry integration.
"""
from .decision import GovernorDecision


class Governor:
    """V2 execution gate — request + tool-level decisions."""

    def __init__(self, tool_registry=None):
        self._registry = tool_registry
        self._decisions: list[GovernorDecision] = []

    # ── Request-level ──────────────────────────────────────────

    def check(self, ctx, message: str) -> GovernorDecision:
        """Check whether an execution request should proceed."""
        if not message or not message.strip():
            return GovernorDecision(allow=False, reason="消息为空")
        if ctx.session_id < 0:
            return GovernorDecision(allow=False, reason="无效会话")
        d = GovernorDecision(allow=True)
        self._decisions.append(d)
        return d

    # ── Tool-level ─────────────────────────────────────────────

    def evaluate(self, tool_name: str, arguments: str,
                 registry=None) -> GovernorDecision:
        """Evaluate whether a tool call should execute.

        Uses ToolRegistry for risk_level lookup.
        CRITICAL tools → deny, HIGH tools → confirm.
        """
        reg = registry or self._registry

        # Look up tool risk level from registry
        risk_level = "MEDIUM"
        if reg:
            entry = reg.get(tool_name)
            if entry:
                risk_level = entry.risk_level

        # Policy mapping
        if risk_level == "CRITICAL":
            d = GovernorDecision(allow=False, reason=f"CRITICAL工具禁止: {tool_name}",
                                risk_level=risk_level, required_action="deny",
                                tool_name=tool_name)
        elif risk_level == "HIGH":
            d = GovernorDecision(allow=True, reason=f"HIGH风险需确认: {tool_name}",
                                risk_level=risk_level, required_action="confirm",
                                tool_name=tool_name)
        elif risk_level == "MEDIUM":
            d = GovernorDecision(allow=True, reason=f"MEDIUM风险: {tool_name}",
                                risk_level=risk_level, required_action="execute",
                                tool_name=tool_name)
        else:
            d = GovernorDecision(allow=True, reason=f"LOW风险工具",
                                risk_level=risk_level, required_action="execute",
                                tool_name=tool_name)

        self._decisions.append(d)
        return d

    # ── Stats ──────────────────────────────────────────────────

    def status(self) -> dict:
        return {
            "total_decisions": len(self._decisions),
            "denied": sum(1 for d in self._decisions if not d.allow),
            "allowed": sum(1 for d in self._decisions if d.allow),
            "recent": [d.to_dict() for d in self._decisions[-5:]],
        }
