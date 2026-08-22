from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import get_db, Base, engine
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.job import Job
from app.routes.jobs import router as job_router
from app.redis import redis_client

app = FastAPI(title=settings.app_name)
app.include_router(job_router)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/items")
def get_tasks(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1")).scalar()
    return {"message": result}

@app.get("/redis-health")
def redis_health_check():
    if redis_client.ping():
        return {"redis": "ok"}
    else:
        raise HTTPException(
            status_code=503, 
            detail="Redis service is unavailable"
    )
    
def _init_db():
    Base.metadata.create_all(bind=engine)


_init_db()