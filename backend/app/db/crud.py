from sqlalchemy.orm import Session
from app.db.models import ResumeDB, EducationDB, WorkExperienceDB
from app.utils.hash_utils import hash_resume
from sqlalchemy.exc import IntegrityError
from app.db.models import ResumeDB, JobRole, SkillGapResult


def save_resume(db: Session, resume_data: dict) -> ResumeDB:
    content_hash = hash_resume(resume_data["raw_text"])
    """Save a structured resume with education & work experience"""
    resume = ResumeDB(
        raw_text=resume_data.get("raw_text", ""),
        name=resume_data.get("name", ""),
        email=resume_data.get("contact", {}).get("email", ""),
        phone=resume_data.get("contact", {}).get("phone", ""),
        skills=resume_data.get("skills", []),
        content_hash=content_hash
    )
    db.add(resume)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Duplicate resume detected")

    for edu in resume_data.get("education", []):
        edu_obj = EducationDB(
            resume_id=resume.id,
            degree=edu.get("degree", ""),
            field=edu.get("field", ""),
            university=edu.get("university", "")
        )
        resume.education.append(edu_obj)
        db.add(edu_obj)

    for exp in resume_data.get("work_experience", []):
        exp_obj = WorkExperienceDB(
            resume_id=resume.id,
            company=exp.get("company", ""),
            position=exp.get("position", ""),
            duration=exp.get("duration", "")
        )
        resume.work_experience.append(exp_obj)
        db.add(exp_obj)

    db.refresh(resume)
    return resume


def get_resume(db: Session, resume_id: int) -> ResumeDB | None:
    return db.query(ResumeDB).filter(ResumeDB.id == resume_id).first()


def get_all_resumes(db: Session):
    return db.query(ResumeDB).all()

def get_or_create_job_role(db: Session, title: str, skills: list[str]) -> JobRole:
    role = db.query(JobRole).filter_by(title=title).first()
    if role:
        return role

    role = JobRole(title=title, skills=skills)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role

def save_skill_gap(
    db: Session,
    resume_id: int,
    ranked_skills: dict
) -> SkillGapResult:
    gap = SkillGapResult(
        resume_id=resume_id,
        core_skills=ranked_skills["core"],
        important_skills=ranked_skills["important"],
        optional_skills=ranked_skills["optional"]
    )
    db.add(gap)
    db.commit()
    db.refresh(gap)
    return gap
