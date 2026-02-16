import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from .activities import print_activity
from .workflows import PrintWorkflow
from .saga_activities import (
    activity_a, activity_b, activity_c,
    compensate_a, compensate_b, compensate_c
)
from .saga_workflow import SagaWorkflow

async def main():
    client = await Client.connect("localhost:7233")
    
    worker = Worker(
        client,
        task_queue="scheduler-v3-task-queue",
        workflows=[PrintWorkflow, SagaWorkflow],
        activities=[
            print_activity,
            activity_a, activity_b, activity_c,
            compensate_a, compensate_b, compensate_c
        ],
    )
    
    print("Worker started. Press Ctrl+C to stop.")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
