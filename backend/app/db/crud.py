# backend/app/db/crud.py
from sqlalchemy.orm import Session
from app.db.models import ResumeDB, EducationDB, WorkExperienceDB

def save_resume(db: Session, resume_data: dict) -> ResumeDB:
    """Save a structured resume with education & work experience"""
    # 1️⃣ Save main resume
    resume = ResumeDB(
        raw_text=resume_data.get("raw_text", ""),
        name=resume_data.get("name", ""),
        email=resume_data.get("contact", {}).get("email", ""),
        phone=resume_data.get("contact", {}).get("phone", ""),
        skills=resume_data.get("skills", [])
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    # 2️⃣ Save education
    for edu in resume_data.get("education", []):
        edu_obj = EducationDB(
            resume_id=resume.id,
            degree=edu.get("degree", ""),
            field=edu.get("field", ""),
            university=edu.get("university", "")
        )
        resume.education.append(edu_obj)
        db.add(edu_obj)

    # 3️⃣ Save work experience
    for exp in resume_data.get("work_experience", []):
        exp_obj = WorkExperienceDB(
            resume_id=resume.id,
            company=exp.get("company", ""),
            position=exp.get("position", ""),
            duration=exp.get("duration", "")
        )
        resume.work_experience.append(exp_obj)
        db.add(exp_obj)

    db.commit()
    return resume


def get_resume(db: Session, resume_id: int) -> ResumeDB | None:
    return db.query(ResumeDB).filter(ResumeDB.id == resume_id).first()


def get_all_resumes(db: Session):
    return db.query(ResumeDB).all()

