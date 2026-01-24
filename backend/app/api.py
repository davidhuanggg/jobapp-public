from fastapi import APIRouter, UploadFile, File
from app.models.resume_models import Resume, RecommendedRole, RecommendationResponse
from app.services.recommendation_service import get_recommendations, explain_role
import tempfile
from app.models.resume_models import Resume
from app.services.extractor_service import extract_resume_data
import os
from app.services.extractor_service import parse_resume_file


router = APIRouter()

@router.post("/parse-and-recommend", response_model=RecommendationResponse)
async def parse_and_recommend(file: UploadFile = File(...)):
    resume_data = await parse_resume_file(file)
    if not resume_data.get("skills"):
        raise HTTPException(status_code=400, detail="No skills extracted from resume.")

    recommendations = get_recommendations(
        skills=resume_data.get("skills", []),
        education=resume_data.get("education", {}),
        work_experience=resume_data.get("work_experience", [])
    )

    for role in recommendations.get("recommended_roles", []):
        role["detailed_explanation"] = explain_role(role["title"])

    return recommendations
