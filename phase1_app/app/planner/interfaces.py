"""MBOS Planner — interface protocol.

PlannerProtocol defines the contract for Planner implementations.
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class PlannerProtocol(Protocol):
    """Decompose a goal into a task plan."""

    def create_plan(self, goal: str):
        ...
