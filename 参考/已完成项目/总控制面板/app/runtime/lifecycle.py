"""MBOS Runtime — lifecycle management.

Owns the execution lifecycle: Receive → Initialize → Execute → Collect → Return.
"""
from .state import ExecutionContext, ExecutionResult, ExecutionStatus


class Lifecycle:
    """Orchestrates the Runtime lifecycle phases."""

    @staticmethod
    def receive(ctx: ExecutionContext) -> ExecutionContext:
        """Phase 1: Receive request. Initialize context."""
        ctx.start()
        return ctx

    @staticmethod
    def initialize(ctx: ExecutionContext) -> ExecutionContext:
        """Phase 2: Initialize. Prepare session/resources."""
        return ctx

    @staticmethod
    def execute(ctx: ExecutionContext) -> ExecutionContext:
        """Phase 3: Execute. Delegate to agent loop (internal)."""
        return ctx

    @staticmethod
    def collect(ctx: ExecutionContext, output: str = "", error: str = None) -> ExecutionResult:
        """Phase 4: Collect result. Build unified ExecutionResult."""
        ctx.complete()
        return ExecutionResult(
            success=error is None,
            output=output,
            error=error,
            metadata={
                "session_id": ctx.session_id,
                "request_id": ctx.request_id,
                "task_id": ctx.task_id,
            },
        )

    @staticmethod
    def fail(ctx: ExecutionContext, error: str) -> ExecutionResult:
        """Handle failure: mark context failed, return error result."""
        ctx.fail()
        return ExecutionResult(
            success=False,
            output="",
            error=error,
            metadata={
                "session_id": ctx.session_id,
                "request_id": ctx.request_id,
            },
        )
