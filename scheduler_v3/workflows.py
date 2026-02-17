from datetime import timedelta
from temporalio import workflow

# Import activity, passing it through the sandbox without reloading the module
with workflow.unsafe.imports_passed_through():
    from .activities import print_activity

@workflow.defn
class PrintWorkflow:
    @workflow.run
    async def run(self, message: str) -> str:
        return await workflow.execute_activity(
            print_activity,
            message,
            start_to_close_timeout=timedelta(seconds=5),
        )
