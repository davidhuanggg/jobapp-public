from sqlalchemy.orm import Session
from app.ingestors.greenhouse import ingest_company as ingest_greenhouse
from app.ingestors.lever import ingest_company as ingest_lever
from app.db.job_crud import save_jobs


def run_ingestion(db: Session, company: str):

    jobs = []

    # Try both ATS types
    try:
        jobs.extend(ingest_greenhouse(company))
    except Exception:
        pass

    try:
        jobs.extend(ingest_lever(company))
    except Exception:
        pass

    saved_count = save_jobs(db, jobs)

    return {
        "company": company,
        "fetched_jobs": len(jobs),
        "saved_jobs": saved_count,
    }

