import asyncio
from typing import Any, Callable, List, TypeVar, Generic, Tuple, Dict
from returns.result import Result, Success, Failure
from returns.future import FutureResult
from temporalio import workflow
from datetime import timedelta

T = TypeVar("T")
R = TypeVar("R")

class SagaError(Exception):
    """Raised when a saga step fails, triggering compensation."""
    def __init__(self, original_error: Exception, step_name: str):
        self.original_error = original_error
        self.step_name = step_name
        super().__init__(f"Step '{step_name}' failed: {original_error}")

class SagaContext:
    """
    Context object that tracks compensations and provides the .step() method
    for executing activities within a Saga.
    """
    def __init__(self):
        self.compensations: List[Callable] = []

    async def step(
        self,
        activity_func: Callable[..., Any],
        args: Any,
        compensation_func: Callable[..., Any],
        step_name: str = "unknown",
        start_to_close_timeout: timedelta = timedelta(seconds=10),
        **kwargs
    ) -> Any:
        """
        Executes an activity.
        On success: returns the result and registers the compensation.
        On failure: raises SagaError to trigger rollback.
        """
        try:
            # Helper to wrap single arg in list if needed, or handle complex args
            # For simplicity in this framework, we assume activity takes 1 arg or list of args
            # Adjust based on your activity signature expectations
            actual_args = args if isinstance(args, (list, tuple)) else [args]

            result = await workflow.execute_activity(
                activity_func,
                *actual_args,
                start_to_close_timeout=start_to_close_timeout,
                **kwargs
            )
            
            # Register compensation (prepended/appended? Stack = LIFO, so append and reverse later)
            self.compensations.append(compensation_func)
            return result
            
        except Exception as e:
            workflow.logger.error(f"Saga step '{step_name}' failed: {e}")
            raise SagaError(e, step_name)

    async def compensate(self):
        """
        Executes registered compensations in reverse order (LIFO).
        """
        workflow.logger.info("Starting Saga compensation...")
        # Reverse the list to get LIFO order
        for comp in reversed(self.compensations):
            try:
                # Assuming compensation takes no args or we'd need to track them too.
                # In strict SAGA, compensation should know what to undo based on stored ID or similar.
                # For this demo, generic compensation is fine.
                await workflow.execute_activity(
                    comp,
                    start_to_close_timeout=timedelta(seconds=5)
                )
            except Exception as e:
                workflow.logger.error(f"Compensation failed: {e}")
        
        workflow.logger.info("Saga compensation complete.")


class SagaRunner:
    """
    Runs the pure functional logic within a Saga Context.
    """
    @staticmethod
    async def run(
        logic_func: Callable[[SagaContext, Any], Any],
        payload: Any
    ) -> Result[Any, Exception]:
        
        ctx = SagaContext()
        
        try:
            # Execute the user's logic
            result = await logic_func(ctx, payload)
            return Success(result)
            
        except SagaError as se:
            workflow.logger.error(f"Saga execution failed. Rolling back. Error: {se}")
            await ctx.compensate()
            return Failure(se.original_error)
            
        except Exception as e:
            workflow.logger.error(f"Unexpected Saga error: {e}")
            await ctx.compensate()
            return Failure(e)
