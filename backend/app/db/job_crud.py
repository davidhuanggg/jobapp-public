from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db.job_models import JobPosting


def save_jobs(db: Session, jobs: list[dict]):
    saved = 0

    for job in jobs:
        db_job = JobPosting(**job)

        try:
            db.add(db_job)
            db.commit()
            saved += 1
        except IntegrityError:
            db.rollback()

    return saved


def get_recent_jobs(db: Session, limit: int = 50):
    return db.query(JobPosting).order_by(JobPosting.id.desc()).limit(limit).all()


def search_jobs_by_title(db: Session, title: str):
    return db.query(JobPosting).filter(
        JobPosting.normalized_title.ilike(f"%{title}%")
    ).all()

