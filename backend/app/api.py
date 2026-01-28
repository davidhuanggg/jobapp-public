from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.recommendation_service import get_recommendations, explain_role
from app.services.extractor_service import extract_resume_data
from app.models.resume_models import Resume, RecommendationResponse
import tempfile
import os
from app.db.db import save_resume, init_db
from app.services.extractor_service import extract_resume_data

router = APIRouter()

init_db()

@router.post("/parse-and-recommend", response_model=RecommendationResponse)
async def parse_and_recommend(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="Resume file is required")

    # Extract resume
    resume_data = await extract_resume_data(file)
    if not resume_data:
        raise HTTPException(status_code=400, detail="Failed to parse resume")

    # Ensure skills exist
    skills = resume_data.get("skills", [])
    if not skills:
        raise HTTPException(status_code=400, detail="No skills extracted from resume")

    education = resume_data.get("education", {})
    work_experience = resume_data.get("work_experience", [])

    # Save to DB
    save_resume({
        "raw_text": resume_data.get("raw_text", ""),
        "skills": skills,
        "education": education,
        "work_experience": work_experience
    })

    # Generate recommendations
    recommendations = get_recommendations(
        skills=skills,
        education=education,
        work_experience=work_experience
    )

    for role in recommendations.get("recommended_roles", []):
        role["detailed_explanation"] = explain_role(role["title"])

    return recommendations


@router.get("/resumes")
def list_resumes():
    """
    Return all resumes stored in the database (for testing/debugging).
    """
    return get_all_resumes()

