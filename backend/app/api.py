from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.extractor_service import extract_resume_data
from app.services.recommendation_service import get_recommendations, explain_role
from app.db.crud import save_resume, get_resume
from app.db.database import SessionLocal
from app.models.resume_models import RecommendationResponse
from app.services.job_skill_service import extract_job_skills
from app.services.skill_gap_service import (
    aggregate_job_skills,
    compute_skill_gap,
    rank_skills,
    build_learning_path_for_role
)
from app.services.job_service import match_role_titles_to_jobs
from app.services.learning_resource_service import build_learning_resources
from pydantic import BaseModel

router = APIRouter()


class MatchJobsRequest(BaseModel):
    resume_id: int | None = None
    role_titles: list[str] | None = None


class LearningResourcesRequest(BaseModel):
    """Strict: must match a resume row from your own `/parse-and-recommend` flow."""
    resume_id: int
    role_titles: list[str] | None = None

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
        "learning_paths": learning_paths,
    }


@router.post("/jobs/match")
async def match_jobs_to_roles(body: MatchJobsRequest, db: Session = Depends(get_db)):
    """
    Find real job postings that match the given role titles.
    Uses job board APIs (e.g. Adzuna) and official company career pages (Greenhouse, Lever).
    """
    if not body.resume_id and (not body.role_titles or len(body.role_titles) == 0):
        raise HTTPException(400, "Provide either `resume_id` or `role_titles`.")

    resume_skills = None
    role_titles: list[str] = body.role_titles or []

    if body.resume_id:
        resume = get_resume(db, body.resume_id)
        if not resume:
            raise HTTPException(404, "Resume not found")
        resume_skills = resume.skills or []

        # If role titles aren't provided, generate them from the saved resume.
        if len(role_titles) == 0:
            # Build education/work-experience lists from stored DB relationships.
            education = [
                {"degree": e.degree, "field": e.field, "institution": e.university}
                for e in (resume.education or [])
            ]
            work_experience = [
                {"company": w.company, "title": w.position, "duration": w.duration}
                for w in (resume.work_experience or [])
            ]

            recommendations = get_recommendations(
                skills=resume_skills,
                education=education,
                work_experience=work_experience,
            )
            role_titles = [r.get("title") for r in recommendations.get("recommended_roles", []) if r.get("title")]

    if len(role_titles) == 0:
        return {"by_role": {}, "sources_used": []}

    return match_role_titles_to_jobs(
        role_titles,
        jobs_per_role=15,
        include_company_jobs=True,
        country="us",
        candidate_skills=resume_skills,
    )


@router.post("/learning-resources")
async def learning_resources(body: LearningResourcesRequest, db: Session = Depends(get_db)):
    """
    Return learning resources for exactly one saved resume.

    Strict behavior: if `resume_id` does not exist, returns 404. No fallback to
    other rows (avoids cross-user leakage in shared DB). For real multi-tenant
    isolation, add auth and tie resumes to `user_id` / session.
    """
    resume = get_resume(db, body.resume_id)
    if not resume:
        raise HTTPException(404, "Resume not found")

    resume_skills = resume.skills or []
    if not resume_skills:
        return {"learning_resources": {}}

    role_titles: list[str] = body.role_titles or []
    if len(role_titles) == 0:
        education = [
            {"degree": e.degree, "field": e.field, "institution": e.university}
            for e in (resume.education or [])
        ]
        work_experience = [
            {"company": w.company, "title": w.position, "duration": w.duration}
            for w in (resume.work_experience or [])
        ]
        recommendations = get_recommendations(
            skills=resume_skills,
            education=education,
            work_experience=work_experience,
        )
        role_titles = [r.get("title") for r in recommendations.get("recommended_roles", []) if r.get("title")]

    learning_paths: dict = {}
    for role_title in role_titles:
        role_skills = extract_job_skills(role_title)
        learning_paths[role_title] = build_learning_path_for_role(
            resume_skills=resume_skills,
            role_skills=role_skills,
        )

    return {"learning_resources": build_learning_resources(learning_paths)}

