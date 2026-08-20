from app.database import Base
from sqlalchemy import String, func, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[JobStatus] = mapped_column(default=JobStatus.queued)
    result: Mapped[Optional[str]] = mapped_column(default=None)
    error: Mapped[Optional[str]] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    completed_at: Mapped[Optional[datetime]] = mapped_column(default=None)

