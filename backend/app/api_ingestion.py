from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.ingestion_service import run_ingestion
from app.db.job_crud import get_recent_jobs, search_jobs_by_title

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/run/{company}")
def run_ingest(company: str, db: Session = Depends(get_db)):
    return run_ingestion(db, company)


@router.get("/status")
def ingest_status(db: Session = Depends(get_db)):
    jobs = get_recent_jobs(db)
    return jobs


@router.get("/jobs/search")
def search_jobs(title: str, db: Session = Depends(get_db)):
    return search_jobs_by_title(db, title)

