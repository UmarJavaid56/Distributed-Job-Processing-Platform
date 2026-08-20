from app.schemas.job import JobCreate, JobRead
from sqlalchemy.orm import Session
from app.database import get_db
from fastapi import Depends, APIRouter
from app.models.job import Job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.post("", status_code=201, response_model=JobRead)
def create_job(body: JobCreate, db: Session = Depends(get_db)) -> JobRead:
    job = Job(name=body.name, payload=body.payload)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job