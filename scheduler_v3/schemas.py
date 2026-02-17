from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID



class SagaPayload(BaseModel):
    failure_rate: float = 0.3
    activities: List[str] = ["A", "B", "C"]

class ScheduleCreate(BaseModel):
    cron_expression: str
    webhook_url: Optional[str] = None
    webhook_payload: Optional[Dict[str, Any]] = {}
    workflow_type: str = "print"  # "print" or "saga"
    saga_payload: Optional[SagaPayload] = None
    tags: Optional[Dict[str, Any]] = {}

class ScheduleUpdate(BaseModel):
    cron_expression: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_payload: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, Any]] = None

class ScheduleData(ScheduleCreate):
    id: UUID
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ScheduleList(BaseModel):
    items: List[ScheduleData]
    total: int
    skip: int
    limit: int
