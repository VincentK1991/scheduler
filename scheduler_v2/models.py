from sqlalchemy import Column, String, JSON, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .database import Base

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
