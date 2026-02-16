from datetime import datetime, timedelta
from uuid import UUID
from typing import Optional, List
import logging
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from temporalio.client import Client, Schedule, ScheduleActionStartWorkflow, ScheduleSpec, ScheduleIntervalSpec, ScheduleUpdateInput, ScheduleUpdate as TemporalScheduleUpdate
from temporalio.service import RPCError

from .database import get_db
from .models import Schedule as ScheduleModel
from .schemas import ScheduleCreate, ScheduleUpdate, ScheduleData, ScheduleList, SagaPayload
from .workflows import PrintWorkflow
from .saga_workflow import SagaWorkflow

# Global Temporal Client
temporal_client: Optional[Client] = None

def set_temporal_client(client: Client):
    global temporal_client
    temporal_client = client

router = APIRouter(prefix="/schedules")
logger = logging.getLogger(__name__)

async def get_current_user(x_user_id: str = Header(...)):
    if not x_user_id:
        raise HTTPException(400, "X-User-ID header required")
    return x_user_id

def _get_schedule_spec(cron_expression: str) -> ScheduleSpec:
    interval_spec = []
    cron_expressions = []

    if cron_expression.startswith("@every"):
         duration_str = cron_expression.replace("@every", "").strip()
         seconds = 0
         if duration_str.endswith("s"):
             seconds = int(duration_str[:-1])
         elif duration_str.endswith("m"):
             seconds = int(duration_str[:-1]) * 60
         elif duration_str.endswith("h"):
             seconds = int(duration_str[:-1]) * 3600
         
         if seconds > 0:
             interval_spec.append(ScheduleIntervalSpec(every=timedelta(seconds=seconds)))
    else:
        # Assume standard cron
        cron_expressions.append(cron_expression)
    
    return ScheduleSpec(
        cron_expressions=cron_expressions,
        intervals=interval_spec
    )


@router.post("", response_model=ScheduleData)
async def create_schedule(
    schedule: ScheduleCreate, 
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not temporal_client:
        raise HTTPException(500, "Temporal client not connected")

    print(f"DEBUG: Received schedule: {schedule.model_dump()}")

    # Save to local DB first
    db_schedule = ScheduleModel(
        user_id=user_id,
        cron_expression=schedule.cron_expression,
        webhook_url=schedule.webhook_url, # Kept for API compatibility, though we print instead
        webhook_payload=schedule.webhook_payload,
        tags=schedule.tags
    )
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)

    # Create Temporal Schedule
    schedule_id = str(db_schedule.id)
    spec = _get_schedule_spec(schedule.cron_expression)

    workflow_to_run = PrintWorkflow.run
    workflow_args = []
    
    if schedule.workflow_type == "saga":
        workflow_to_run = SagaWorkflow.run
        # Use provided saga_payload or default
        payload = schedule.saga_payload or SagaPayload()
        workflow_args = [payload]
    else:
        # Default to PrintWorkflow
        workflow_args = [f"Schedule {schedule_id} triggered! Payload: {schedule.webhook_payload}"]

    try:
        await temporal_client.create_schedule(
            schedule_id,
            Schedule(
                action=ScheduleActionStartWorkflow(
                    workflow_to_run,
                    args=workflow_args,
                    id=f"workflow-{schedule_id}",
                    task_queue="scheduler-v3-task-queue",
                ),
                spec=spec,
            ),
        )
    except Exception as e:
        logger.error(f"Failed to create Temporal schedule: {e}")
        db.delete(db_schedule)
        db.commit()
        raise HTTPException(500, f"Failed to create schedule in Temporal: {e}")

    return db_schedule

@router.get("", response_model=ScheduleList)
def list_schedules(
    user_id: str = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    schedules = db.query(ScheduleModel)\
        .filter(ScheduleModel.user_id == user_id)\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    total = db.query(ScheduleModel).filter(ScheduleModel.user_id == user_id).count()
    
    return {"items": schedules, "total": total, "skip": skip, "limit": limit}

@router.patch("/{schedule_id}", response_model=ScheduleData)
async def update_schedule(
    schedule_id: UUID, 
    updates: ScheduleUpdate, 
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    schedule = db.query(ScheduleModel).filter(
        ScheduleModel.id == schedule_id,
        ScheduleModel.user_id == user_id
    ).first()
    
    if not schedule:
        raise HTTPException(404, "Schedule not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)
    
    db.commit()
    db.refresh(schedule)

    # Update Temporal if cron expression changed
    if temporal_client and updates.cron_expression:
        try:
            handle = temporal_client.get_schedule_handle(str(schedule_id))
            
            async def update_schedule_func(input: ScheduleUpdateInput) -> TemporalScheduleUpdate:
                schedule_update = TemporalScheduleUpdate(
                    schedule=input.description.schedule
                )
                # Update spec
                schedule_update.schedule.spec = _get_schedule_spec(updates.cron_expression)
                return schedule_update

            await handle.update(update_schedule_func)
            
        except Exception as e:
            logger.error(f"Failed to update Temporal schedule: {e}")
            # Non-fatal for DB consistency, but bad for scheduler
            raise HTTPException(500, f"Failed to update Temporal schedule: {e}")

    return schedule

@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: UUID, 
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get from DB
    schedule = db.query(ScheduleModel).filter(
        ScheduleModel.id == schedule_id,
        ScheduleModel.user_id == user_id
    ).first()
    
    if not schedule:
        raise HTTPException(404, "Schedule not found")

    # Delete from Temporal
    if temporal_client:
        try:
            handle = temporal_client.get_schedule_handle(str(schedule_id))
            await handle.delete()
        except RPCError:
             logger.warning(f"Schedule {schedule_id} not found in Temporal")
        except Exception as e:
             logger.error(f"Error deleting Temporal schedule: {e}")

    # Delete from DB
    db.delete(schedule)
    db.commit()

    return {"status": "deleted"}
