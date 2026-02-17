from fastapi import APIRouter, HTTPException, Depends
from temporalio.client import Client, Schedule, ScheduleActionStartWorkflow, ScheduleSpec, ScheduleIntervalSpec
from typing import Optional
import logging
from uuid import uuid4
from datetime import timedelta

# Reuse schemas from v3 to minimize duplication, or define new ones if needed
# For now, simplistic payload
from pydantic import BaseModel

class FunctionalScheduleCreate(BaseModel):
    cron_expression: str = "* * * * *"
    payload: dict = {}

router = APIRouter(prefix="/schedules_v3_1")
logger = logging.getLogger(__name__)

temporal_client: Optional[Client] = None

def set_temporal_client(client: Client):
    global temporal_client
    temporal_client = client

@router.post("")
async def create_schedule(schedule: FunctionalScheduleCreate):
    if not temporal_client:
        raise HTTPException(500, "Temporal client not connected")

    schedule_id = str(uuid4())
    
    # Simple Spec parsing for demo
    interval = ScheduleIntervalSpec(every=timedelta(minutes=1))
    spec = ScheduleSpec(intervals=[interval])
    
    from .functional_workflow import FunctionalDagWorkflow

    try:
        await temporal_client.create_schedule(
            schedule_id,
            Schedule(
                action=ScheduleActionStartWorkflow(
                    FunctionalDagWorkflow.run,
                    args=[schedule.payload],
                    id=f"workflow-v3-1-{schedule_id}",
                    task_queue="scheduler-v3-1-task-queue",
                ),
                spec=spec,
            ),
        )
    except Exception as e:
        logger.error(f"Failed to create schedule: {e}")
        raise HTTPException(500, f"Failed to create schedule: {e}")

    return {"id": schedule_id, "status": "created", "type": "functional_dag"}
