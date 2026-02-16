import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from .activities import print_activity
from .workflows import PrintWorkflow

async def main():
    client = await Client.connect("localhost:7233")
    
    worker = Worker(
        client,
        task_queue="scheduler-v3-task-queue",
        workflows=[PrintWorkflow],
        activities=[print_activity],
    )
    
    print("Worker started. Press Ctrl+C to stop.")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
