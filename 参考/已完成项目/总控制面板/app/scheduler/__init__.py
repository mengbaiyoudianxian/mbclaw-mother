"""MBOS Scheduler v1 — LLM dispatch layer.

Scheduler is the only module that makes LLM HTTP calls.
Runtime delegates all LLM requests to Scheduler.dispatch().
"""
from .scheduler import Scheduler
from .interfaces import SchedulerProtocol

__all__ = ["Scheduler", "SchedulerProtocol"]
