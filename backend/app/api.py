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
    rank_skills,
    build_learning_path_for_role
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
    resume_data = await extract_resume_data(file)
    if not resume_data:
        raise HTTPException(400, "Failed to parse resume")

    resume_skills = resume_data.get("skills", [])
    education = resume_data.get("education", {})
    work_experience = resume_data.get("work_experience", [])

    if not resume_skills:
        raise HTTPException(400, "No skills extracted from resume")

    try:
        saved_resume = save_resume(db, resume_data)
    except ValueError:
        raise HTTPException(409, "Resume already uploaded")

    recommendations = get_recommendations(
        skills=resume_skills,
        education=education,
        work_experience=work_experience
    )

    roles = recommendations.get("recommended_roles", [])

    learning_paths = {}

    for role in roles:
        role_title = role["title"]

        # Extract skills required for THIS role
        role_skills = extract_job_skills(role_title)

        # Compute gap vs resume
        learning_paths[role_title] = build_learning_path_for_role(
            resume_skills=resume_skills,
            role_skills=role_skills
        )

        # Add explanation
        role["detailed_explanation"] = explain_role(role_title)

    return {
        "resume_id": saved_resume.id,
        "recommendations": roles,
        "learning_paths": learning_paths
    }

