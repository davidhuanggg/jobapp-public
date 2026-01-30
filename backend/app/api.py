from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.extractor_service import extract_resume_data
from app.services.recommendation_service import get_recommendations, explain_role
from app.db.crud import save_resume
from app.db.database import SessionLocal
from app.models.resume_models import RecommendationResponse
from app.services.job_skill_service import extract_job_skills
from app.services.skill_gap_service import (
    aggregate_job_skills,
    compute_skill_gap,
    rank_skills
)

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/parse-and-recommend")
async def parse_and_recommend(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file:
        raise HTTPException(400, "Resume file is required")

    resume_data = await extract_resume_data(file)
    if not resume_data:
        raise HTTPException(400, "Failed to parse resume")

    skills = resume_data.get("skills", [])
    education = resume_data.get("education", {})
    work_experience = resume_data.get("work_experience", [])

    if not skills:
        raise HTTPException(400, "No skills extracted from resume")

    try:
        saved_resume = save_resume(db, resume_data)
    except ValueError:
        raise HTTPException(409, "This resume has already been uploaded")

    recommendations = get_recommendations(
        skills=skills,
        education=education,
        work_experience=work_experience
    )

    roles = recommendations.get("recommended_roles", [])

    for role in roles:
        role["detailed_explanation"] = explain_role(role["title"])

    job_skill_lists = []

    for role in roles:
        role_skills = extract_job_skills(role["title"])
        job_skill_lists.append(role_skills)

    if job_skill_lists:
        aggregated_skills = aggregate_job_skills(job_skill_lists)
        skill_gap = compute_skill_gap(skills, aggregated_skills)
        learning_path = rank_skills(skill_gap, len(job_skill_lists))
    else:
        learning_path = {
            "core": [],
            "important": [],
            "optional": []
        }

    return {
        "resume_id": saved_resume.id,
        "recommendations": roles,
        "learning_path": learning_path
    }

