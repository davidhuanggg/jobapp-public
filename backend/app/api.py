from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.extractor_service import extract_resume_data
from app.services.recommendation_service import get_recommendations, explain_role
from app.db.crud import save_resume
from app.db.database import SessionLocal
from app.models.resume_models import RecommendationResponse

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/parse-and-recommend", response_model=RecommendationResponse)
async def parse_and_recommend(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file:
        raise HTTPException(status_code=400, detail="Resume file is required")

    # Extract structured resume
    resume_data = await extract_resume_data(file)

    if not resume_data.get("skills"):
        raise HTTPException(status_code=400, detail="No skills extracted from resume.")

    # Save resume to DB
    try:
        saved_resume = save_resume(db, resume_data)
    except ValueError:
        raise HTTPException(
            status_code=409,
            detail="This resume has already been uploaded"
        )
    # Generate recommendations
    recommendations = get_recommendations(
        skills=resume_data.get("skills", []),
        education=resume_data.get("education", []),
        work_experience=resume_data.get("work_experience", [])
    )

    # Add explanations
    for role in recommendations.get("recommended_roles", []):
        role["detailed_explanation"] = explain_role(role["title"])

    return recommendations

