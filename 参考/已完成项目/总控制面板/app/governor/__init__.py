"""MBOS Governor v1 — execution gate.

Governor checks every execution request before the agent loop.
V1: empty message → deny, invalid context → deny, else allow.
"""
from .decision import GovernorDecision
from .interfaces import GovernorProtocol
from .governor import Governor

__all__ = ["Governor", "GovernorDecision", "GovernorProtocol"]
