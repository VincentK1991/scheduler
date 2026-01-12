from fastapi import APIRouter, Depends, Query, HTTPException, Header
from sqlalchemy.orm import Session
from croniter import croniter, croniter_range
from uuid import UUID
import httpx
from typing import List, Optional, Dict, Any
import datetime
import logging

from .database import get_db
from .models import Schedule
from .schemas import ScheduleCreate, ScheduleUpdate, ScheduleData, ScheduleList
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# We need a way to reference the scheduler globally or pass it in.
# For simplicity in this POC, we'll assign it here from main, or use a global.
# Ideally, we'd use dependency injection or a singleton.
scheduler: Optional[BackgroundScheduler] = None

def set_scheduler(s: BackgroundScheduler):
    global scheduler
    scheduler = s

router = APIRouter(prefix="/schedules")
logger = logging.getLogger(__name__)

async def get_current_user(x_user_id: str = Header(...)):
    if not x_user_id:
        raise HTTPException(400, "X-User-ID header required")
    return x_user_id

def execute_webhook(schedule_id_str: str, db_url: str = None):
    """
    Actual webhook execution function.
    
    Note: APScheduler runs this in a thread pool.
    We need to create a new DB session here if we need DB access, 
    but for the webhook call we mainly need the URL and payload.
    Since we don't want to pass complex objects to APScheduler jobs (serialization issues),
    we pass IDs.
    
    However, to keep it simple and robust, we can query the DB to get the latest details.
    """
    import asyncio
    
    # Create a new engine/session for this thread
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from .models import Schedule
    from .database import SQLALCHEMY_DATABASE_URL
    
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id_str).first()
        if not schedule:
            logger.error(f"Schedule {schedule_id_str} not found during execution")
            return

        # We must run the async http call in a new event loop or synchronously
        # Since we are in a thread, we can use httpx synchronous client or asyncio.run
        try:
           with httpx.Client(timeout=30.0) as client:
                response = client.post(schedule.webhook_url, json=schedule.webhook_payload)
                logger.info(f"Webhook executed for {schedule_id_str}. Status: {response.status_code}")
        except Exception as e:
            logger.error(f"Webhook execution failed for {schedule_id_str}: {e}")

    finally:
        db.close()

# Helper to parse cron string for APScheduler
# APScheduler CronTrigger takes: year, month, day, week, day_of_week, hour, minute, second
# But from_crontab is the easiest way if it supports standard cron
def get_trigger(cron_str: str):
    return CronTrigger.from_crontab(cron_str)


@router.post("", response_model=ScheduleData)
def create_schedule(
    schedule: ScheduleCreate, 
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if schedule.cron_expression.startswith("@every"):
        # Very basic parsing for "@every 5s", "@every 10m"
        # Dkron syntax: @every <duration>
        duration_str = schedule.cron_expression.replace("@every", "").strip()
        
        seconds = 0
        if duration_str.endswith("s"):
            seconds = int(duration_str[:-1])
        elif duration_str.endswith("m"):
            seconds = int(duration_str[:-1]) * 60
        elif duration_str.endswith("h"):
            seconds = int(duration_str[:-1]) * 3600
        else:
            raise HTTPException(400, "Unsupported interval format. Use xs, xm, or xh.")
            
        trigger = IntervalTrigger(seconds=seconds)
    else:
        if not croniter.is_valid(schedule.cron_expression):
            raise HTTPException(400, "Invalid cron expression")
        trigger = get_trigger(schedule.cron_expression)

    db_schedule = Schedule(
        user_id=user_id,
        cron_expression=schedule.cron_expression,
        webhook_url=schedule.webhook_url,
        webhook_payload=schedule.webhook_payload,
        tags=schedule.tags
    )
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)

    if scheduler:
        scheduler.add_job(
            execute_webhook,
            trigger=trigger,
            id=str(db_schedule.id),
            args=[str(db_schedule.id)]
        )

    return db_schedule

@router.get("", response_model=ScheduleList)
def list_schedules(
    user_id: str = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    schedules = db.query(Schedule)\
        .filter(Schedule.user_id == user_id)\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    total = db.query(Schedule).filter(Schedule.user_id == user_id).count()
    
    return {"items": schedules, "total": total, "skip": skip, "limit": limit}

@router.patch("/{schedule_id}", response_model=ScheduleData)
def update_schedule(
    schedule_id: UUID, 
    updates: ScheduleUpdate, 
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.user_id == user_id
    ).first()
    
    if not schedule:
        raise HTTPException(404, "Schedule not found")
    
    if updates.cron_expression and not croniter.is_valid(updates.cron_expression):
        raise HTTPException(400, "Invalid cron expression")

    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)
    
    db.commit()
    db.refresh(schedule)

    if scheduler and updates.cron_expression:
        try:
            scheduler.reschedule_job(
                str(schedule_id),
                trigger=get_trigger(schedule.cron_expression)
            )
        except Exception as e:
            logger.warning(f"Failed to reschedule job {schedule_id}: {e}")
            # It might be that the job was missing from the scheduler but present in DB
            # Try adding it if it's missing (upsert logic basically)
            scheduler.add_job(
                execute_webhook,
                trigger=get_trigger(schedule.cron_expression),
                id=str(schedule_id),
                args=[str(schedule_id)],
                replace_existing=True
            )

    return schedule

@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: UUID, 
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.user_id == user_id
    ).first()
    
    if not schedule:
        raise HTTPException(404, "Schedule not found")

    if scheduler:
        try:
            scheduler.remove_job(str(schedule_id))
        except Exception as e:
            logger.warning(f"Job {schedule_id} not found in scheduler: {e}")

    db.delete(schedule)
    db.commit()

    return {"status": "deleted"}
