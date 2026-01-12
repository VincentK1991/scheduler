following the working # TODO.md

I want to create a simple python app for task scheduling 
with full control unlike using dkron (where i have to use dkron's API to create/update/delete schedules).

here the app will use its own persistence database and python App to schedule a webhook action.

this will be a simple docker-compose stack with
- postgresql
- python app using fastapi (CRUD) and APScheduler (cron engine)

FastAPI App
├─ API Endpoints (CRUD)
├─ APScheduler (cron engine)
└─ PostgreSQL (job storage)

# main.py
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from contextlib import asynccontextmanager

jobstores = {
    'default': SQLAlchemyJobStore(url='postgresql://...')
}

scheduler = BackgroundScheduler(jobstores=jobstores)

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

# models.py
from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Schedule(Base):
    __tablename__ = "schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, index=True, nullable=False)
    cron_expression = Column(String, nullable=False)
    webhook_url = Column(String, nullable=False)
    webhook_payload = Column(JSON, nullable=False)
    tags = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

# routes.py
from fastapi import APIRouter, Depends, Query
from croniter import croniter
import httpx

router = APIRouter(prefix="/schedules")

async def execute_webhook(schedule_id: str):
    """Actual webhook execution function"""
    schedule = get_schedule_from_db(schedule_id)
    async with httpx.AsyncClient() as client:
        await client.post(
            schedule.webhook_url,
            json=schedule.webhook_payload,
            timeout=30.0
        )

@router.post("")
async def create_schedule(schedule: ScheduleCreate, user_id: str = Depends(get_current_user)):
    # Validate cron expression
    if not croniter.is_valid(schedule.cron_expression):
        raise HTTPException(400, "Invalid cron expression")
    
    # Save to DB
    db_schedule = Schedule(
        user_id=user_id,
        cron_expression=schedule.cron_expression,
        webhook_url=schedule.webhook_url,
        webhook_payload=schedule.webhook_payload,
        tags=schedule.tags
    )
    db.add(db_schedule)
    db.commit()
    
    # Add to scheduler
    scheduler.add_job(
        execute_webhook,
        trigger='cron',
        id=str(db_schedule.id),
        args=[str(db_schedule.id)],
        **parse_cron_expression(schedule.cron_expression)
    )
    
    return db_schedule

@router.get("")
async def list_schedules(
    user_id: str = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100)
):
    schedules = db.query(Schedule)\
        .filter(Schedule.user_id == user_id)\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    total = db.query(Schedule).filter(Schedule.user_id == user_id).count()
    
    return {"items": schedules, "total": total, "skip": skip, "limit": limit}

@router.patch("/{schedule_id}")
async def update_schedule(schedule_id: UUID, updates: ScheduleUpdate, user_id: str = Depends(get_current_user)):
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.user_id == user_id
    ).first()
    
    if not schedule:
        raise HTTPException(404)
    
    # Update DB
    for field, value in updates.dict(exclude_unset=True).items():
        setattr(schedule, field, value)
    db.commit()
    
    # Update scheduler
    scheduler.reschedule_job(
        str(schedule_id),
        trigger='cron',
        **parse_cron_expression(schedule.cron_expression)
    )
    
    return schedule

@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: UUID, user_id: str = Depends(get_current_user)):
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.user_id == user_id
    ).first()
    
    if not schedule:
        raise HTTPException(404)
    
    # Remove from scheduler
    scheduler.remove_job(str(schedule_id))
    
    # Remove from DB
    db.delete(schedule)
    db.commit()
    
    return {"status": "deleted"}