from app.models.job import JobStatus
from pydantic import BaseModel, ConfigDict
from typing import Optional
import uuid
from datetime import datetime

class JobCreate(BaseModel):
    name: str
    payload: dict

class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    name: str
    payload: dict
    id: uuid.UUID
    status: JobStatus
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None