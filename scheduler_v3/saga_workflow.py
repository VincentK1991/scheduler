from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from .saga_activities import (
        activity_a, activity_b, activity_c,
        compensate_a, compensate_b, compensate_c
    )
    from .schemas import SagaPayload

@workflow.defn
class SagaWorkflow:
    @workflow.run
    async def run(self, payload: SagaPayload) -> str:
        compensations = []
        
        # Retry policy for the activities (simulate transient failures)
        # We fail fast here to trigger compensation quickly for the demo
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_attempts=3, 
        )

        try:
            # Step A
            if "A" in payload.activities:
                await workflow.execute_activity(
                    activity_a,
                    payload.failure_rate,
                    start_to_close_timeout=timedelta(seconds=5),
                    retry_policy=retry_policy,
                )
                compensations.append(compensate_a)

            # Step B
            if "B" in payload.activities:
                await workflow.execute_activity(
                    activity_b,
                    payload.failure_rate,
                    start_to_close_timeout=timedelta(seconds=5),
                    retry_policy=retry_policy,
                )
                compensations.append(compensate_b)

            # Step C
            if "C" in payload.activities:
                await workflow.execute_activity(
                    activity_c,
                    payload.failure_rate,
                    start_to_close_timeout=timedelta(seconds=5),
                    retry_policy=retry_policy,
                )
                compensations.append(compensate_c)
            
            return "SAGA Completed Successfully"

        except Exception as e:
            workflow.logger.error(f"SAGA Failed: {e}. Starting compensation.")
            
            # Execute compensations in reverse order
            for comp in reversed(compensations):
                try:
                    await workflow.execute_activity(
                        comp,
                        start_to_close_timeout=timedelta(seconds=5),
                    )
                except Exception as ce:
                    workflow.logger.error(f"Compensation failed: {ce}")
            
            raise e
