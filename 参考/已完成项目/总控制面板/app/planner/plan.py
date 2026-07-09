"""MBOS Planner — plan types.

TaskPlan and PlanStep represent a decomposed goal.
V1: trivial decomposition (goal → single step).
"""
from dataclasses import dataclass, field


@dataclass
class PlanStep:
    """A single step in a task plan.

    Attributes:
        id: Step number (1-indexed).
        description: Human-readable step description.
        status: 'pending', 'running', 'done', or 'failed'.
    """
    id: int
    description: str
    status: str = "pending"


@dataclass
class TaskPlan:
    """A goal decomposed into ordered steps.

    Attributes:
        goal: Original user goal.
        steps: Ordered list of PlanStep.
    """
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
