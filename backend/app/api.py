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
from app.services.job_matching_service import find_matching_jobs
from pydantic import BaseModel

router = APIRouter()


class MatchJobsRequest(BaseModel):
    role_titles: list[str]

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

    # Match recommendations to real jobs (job board APIs + official company career pages)
    matching = find_matching_jobs(
        roles,
        jobs_per_role=10,
        include_company_jobs=True,
    )
    for role in roles:
        role["matching_jobs"] = matching["by_role"].get(role["title"], [])

    return {
        "resume_id": saved_resume.id,
        "recommendations": roles,
        "learning_paths": learning_paths,
        "matching_jobs_sources": matching["sources_used"],
    }


@router.post("/jobs/match")
async def match_jobs_to_roles(body: MatchJobsRequest):
    """
    Find real job postings that match the given role titles.
    Uses job board APIs (e.g. Adzuna) and official company career pages (Greenhouse, Lever).
    """
    if not body.role_titles:
        return {"by_role": {}, "sources_used": []}
    roles = [{"title": t} for t in body.role_titles]
    return find_matching_jobs(roles, jobs_per_role=15, include_company_jobs=True)

