import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker

logging.basicConfig(level=logging.INFO)


from .functional_workflow import FunctionalDagWorkflow
from .dag_activities import (
    activity_a, activity_b, activity_d, activity_e,
    compensate_a, compensate_b, compensate_d, compensate_e
)

async def main():
    import os
    temporal_addr = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    client = await Client.connect(temporal_addr)
    
    worker = Worker(
        client,
        task_queue="scheduler-v3-1-task-queue",
        workflows=[FunctionalDagWorkflow],
        activities=[
            activity_a, activity_b, activity_d, activity_e,
            compensate_a, compensate_b, compensate_d, compensate_e
        ],
    )
    
    print("Worker v3.1 started. Press Ctrl+C to stop.")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
