# backend/app/api.py

from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.recommendation_service import get_recommendations, explain_role
from app.services.extractor_service import extract_resume_data
from app.models.resume_models import Resume, RecommendationResponse
import tempfile
import os

router = APIRouter()


@router.post("/parse-and-recommend", response_model=RecommendationResponse)
async def parse_and_recommend(file: UploadFile = File(...)):
    """
    Upload a resume file, parse it for skills, education, and work experience,
    then return recommended job roles with explanations.
    """
    if not file:
        raise HTTPException(status_code=400, detail="Resume file is required")

    # Save uploaded file temporarily
    suffix = os.path.splitext(file.filename)[1] or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    # Extract structured resume data
    resume_data = extract_resume_data(tmp_path)
    os.remove(tmp_path)

    if not resume_data:
        raise HTTPException(status_code=400, detail="Failed to parse resume")

    skills = resume_data.get("skills", [])
    education = resume_data.get("education", {})
    work_experience = resume_data.get("work_experience", [])

    if not skills:
        raise HTTPException(
            status_code=400,
            detail="No skills extracted from resume. Cannot generate recommendations"
        )

    # Generate recommendations based on structured resume data
    recommendations = get_recommendations(
        skills=skills,
        education=education,
        work_experience=work_experience
    )

    # Add detailed explanations for each recommended role
    for role in recommendations.get("recommended_roles", []):
        role["detailed_explanation"] = explain_role(role["title"])

    return recommendations
