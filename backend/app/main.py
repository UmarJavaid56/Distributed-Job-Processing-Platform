from fastapi import FastAPI, Depends
from app.config import settings
from app.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import text

app = FastAPI(title=settings.app_name)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/items")
def get_tasks(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1")).scalar()
    return {"message": result}