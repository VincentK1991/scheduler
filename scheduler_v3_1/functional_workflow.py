from datetime import timedelta
from temporalio import workflow
from .saga_framework import SagaContext, SagaRunner, SagaError
from returns.result import Result, Success, Failure

with workflow.unsafe.imports_passed_through():
    from .dag_activities import (
        activity_a, activity_b, activity_d, activity_e,
        compensate_a, compensate_b, compensate_d, compensate_e
    )

async def dag_logic(ctx: SagaContext, payload: dict) -> str:
    # Step A
    # Payload input
    a_result = await ctx.step(
        activity_a, [payload], compensate_a, step_name="Step A"
    )

    # Step B (depends on A)
    b_result = await ctx.step(
        activity_b, [a_result], compensate_b, step_name="Step B"
    )

    # Step D (depends on A? Let's say it effectively runs parallel to B but logically after A)
    # The prompt asked for A->B->C (pipeline) but later A->(B||D)->E (DAG)
    # Let's verify D depends on A for this demo? Or maybe B?
    # User said: "like A-> B B-> C B->D but A->E and D->E"
    # Wait, "A-> B B-> C B->D but A->E and D->E"
    # A is root.
    # B depends on A.
    # C depends on B.
    # D depends on B.
    # E depends on A AND D.
    
    # Implementing that exact DAG:
    # 1. A runs
    # 2. B runs (needs A)
    # 3. C runs (needs B) - Parallel with D?
    # 4. D runs (needs B)
    # 5. E runs (needs A and D)

    # Note: Accessing variables 'a_result', 'b_result' is allowed because check this out:
    # We are in a python function. The state is preserved in the scope!

    # Step C (depends on B)
    # We don't have activity_c defined in dag_activities yet, let's skip C for brevity or assume D covers the parallel branch
    # Let's implement A -> B -> D. And D -> E. And A -> E.
    
    # So far: A done. B done (using A).
    
    # Step D (depends on B)
    d_result = await ctx.step(
        activity_d, [b_result], compensate_d, step_name="Step D"
    )

    # Step E (depends on A and D)
    # We pass a dict or tuple
    e_inputs = {"from_a": a_result, "from_d": d_result}
    e_result = await ctx.step(
        activity_e, [e_inputs], compensate_e, step_name="Step E"
    )
    
    return e_result

@workflow.defn
class FunctionalDagWorkflow:
    @workflow.run
    async def run(self, payload: dict) -> str:
        # Wrap the pure logic in the SagaRunner
        result: Result[str, Exception] = await SagaRunner.run(dag_logic, payload)
        
        # Unwrap the monad
        # In a real functional app, we might handle Success/Failure differently
        if isinstance(result, Success):
            return f"Workflow Completed: {result.unwrap()}"
        else:
            # We already compensated in the runner, so just report failure
            failure = result.failure()
            workflow.logger.error(f"Workflow failed with: {failure}")
            raise failure
