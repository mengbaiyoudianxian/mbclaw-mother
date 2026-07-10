"""MBOS Planner v1 — goal decomposition.

Planner converts a user goal into a TaskPlan with ordered steps.
V1: trivial — goal wrapped as single step. No LLM, no execution.
"""
from .plan import TaskPlan, PlanStep


class Planner:
    """V1 planner — wraps goal as single step.

    V1 behavior: every goal becomes one PlanStep.
    Future: multi-step decomposition via LLM or rule-based strategies.

    Usage:
        p = Planner()
        plan = p.create_plan("整理文件")
        # plan.steps[0].description == "整理文件"
    """

    def create_plan(self, goal: str) -> TaskPlan:
        """Decompose a goal into a TaskPlan.

        V1: returns single-step plan. Empty/whitespace goal → empty steps.

        Args:
            goal: User goal text.

        Returns:
            TaskPlan with goal and steps.
        """
        if not goal or not goal.strip():
            return TaskPlan(goal=goal, steps=[])

        return TaskPlan(
            goal=goal,
            steps=[
                PlanStep(id=1, description=goal.strip())
            ]
        )
