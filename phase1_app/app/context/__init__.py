"""MBOS Context Engine v1 — short-term context management.

ContextEngine assembles LLM messages from session WorkingMemory:
system prompt + memory recall + conversation history[-20:].

WorkingMemory holds per-session conversation state with auto-compression.
"""
from .working_memory import WorkingMemory
from .engine import ContextEngine
from .interfaces import ContextEngineProtocol

__all__ = ["ContextEngine", "ContextEngineProtocol", "WorkingMemory"]
