from fastapi import FastAPI, Depends
from app.config import settings
from app.database import get_db, Base, engine
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.job import Job
from app.routes.jobs import router as job_router

app = FastAPI(title=settings.app_name)
app.include_router(job_router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/items")
def get_tasks(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1")).scalar()
    return {"message": result}

def _init_db():
    Base.metadata.create_all(bind=engine)


_init_db()