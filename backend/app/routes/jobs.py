from app.schemas.job import JobCreate, JobRead
from sqlalchemy.orm import Session
from app.database import get_db
from fastapi import Depends, APIRouter, HTTPException, status, Query
from app.models.job import Job, JobStatus
from sqlalchemy import select
from datetime import datetime, timezone
import uuid


router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.post("", status_code=201, response_model=JobRead)
def create_job(body: JobCreate, db: Session = Depends(get_db)) -> JobRead:
    job = Job(name=body.name, payload=body.payload)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

@router.get("", response_model=list[JobRead])
def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[JobRead]:
    stmt = (
        select(Job)
        .order_by(Job.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    jobs = db.scalars(stmt).all()
    return jobs

@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> JobRead:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    return job

@router.delete("/{job_id}", response_model=JobRead)
def cancel_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> JobRead:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    if job.status != JobStatus.queued:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job with ID {job_id} is {job.status}."
        )

    job.status = JobStatus.cancelled
    job.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job
