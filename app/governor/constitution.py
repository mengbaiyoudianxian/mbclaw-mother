"""MBOS Governor — Constitution rules.

The Constitution defines immutable safety rules that the Governor
must enforce before any execution proceeds.

Rules are evaluated in order. First matching deny rule stops evaluation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ConstitutionRule:
    """A single safety rule in the Constitution.

    Attributes:
        name: Rule identifier for logging/reporting.
        description: Human-readable rule description.
        pattern: Regex pattern to match against message content.
        risk_level: Risk level assigned when this rule triggers.
        deny: True if matching this rule means denying the request.
    """
    name: str
    description: str
    pattern: str
    risk_level: str
    deny: bool = True


# ── MBOS Constitution ────────────────────────────────────────

CONSTITUTION: list[ConstitutionRule] = [
    ConstitutionRule(
        name="no_token_leak",
        description="禁止泄露Token/API密钥",
        pattern=r"""(?:api[_\s]?key|api[_\s]?secret|access[_\s]?token
                   |bearer\s+[A-Za-z0-9\-_]{20,}|sk-[A-Za-z0-9]{12,}
                   |Authorization:\s*Bearer)""",
        risk_level="critical",
    ),
    ConstitutionRule(
        name="no_delete_system",
        description="禁止删除核心系统文件",
        pattern=r"""rm\s+(-rf?\s+)?/(etc|boot|bin|sbin|lib|sys|proc|dev)(?:\s|/|$)
                   |rm\s+-rf?\s+/$
                   |del\s+/[CW]:\\Windows
                   |format\s+(C:|/)""",
        risk_level="critical",
    ),
    ConstitutionRule(
        name="no_modify_security",
        description="禁止修改安全模块",
        pattern=r"""(?:chmod\s+777|chown\s+[^ ]+\s+/(etc/passwd|etc/shadow)
                   |iptables\s+-F|ufw\s+disable|setenforce\s+0
                   |sestatus|systemctl\s+stop\s+(?:firewalld|iptables|ufw))""",
        risk_level="critical",
    ),
    ConstitutionRule(
        name="no_bypass_permission",
        description="禁止绕过权限",
        pattern=r"""(?:sudo\s+(?!ls|whoami|id|pwd|echo).*
                   |su\s+-|sudo\s+su
                   |pkexec|doas)""",
        risk_level="high",
    ),
    ConstitutionRule(
        name="critical_auto_deny",
        description="CRITICAL风险自动拒绝 — 系统破坏性命令",
        pattern=r"""(?:shutdown|reboot|halt|poweroff|init\s+[06]
                   |mkfs\.|dd\s+if=|mkswap
                   |:\(\)\s*\{\s*:\|:&\s*\};:
                   |wget\s+.*\|\s*(?:ba)?sh
                   |curl\s+.*\|\s*(?:ba)?sh)""",
        risk_level="critical",
    ),
]
