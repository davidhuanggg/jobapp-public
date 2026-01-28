from sqlalchemy.orm import Session
from app.db.models import ResumeDB

def save_resume(db: Session, raw_text: str) -> ResumeDB:
    resume = ResumeDB(raw_text=raw_text)
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume

def get_resume(db: Session, resume_id: int) -> ResumeDB | None:
    return db.query(ResumeDB).filter(ResumeDB.id == resume_id).first()

