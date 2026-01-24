# app/services/resume_analyzer.py
import os
import tempfile
from fastapi import UploadFile
from app.models.resume_models import Resume, RecommendationResponse
from app.services.extractor_service import extract_resume_data
from app.services.recommendation_service import get_recommendations, explain_role

class ResumeAnalyzer:
    def __init__(self):
        self.resume_data: Resume | None = None

    def parse_resume(self, file: UploadFile):
        """
        Parse a resume file and store its data.
        """
        # Save to temporary file
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file.file.read())
            tmp_path = tmp.name

        # Extract resume data
        self.resume_data = extract_resume_data(tmp_path)
        # Clean up temp file
        os.remove(tmp_path)

        return self.resume_data

    def recommend_jobs(self) -> dict:
        """
        Recommend jobs based on the previously parsed resume.
        Raises an error if no resume has been parsed.
        """
        if not self.resume_data or not self.resume_data.raw_text.strip():
            raise ValueError("No resume uploaded. Please parse a resume first.")

        # Get recommended roles
        recommendations = get_recommendations(self.resume_data.raw_text)

        # Add detailed explanation for each role
        for role in recommendations.get("recommended_roles", []):
            role["detailed_explanation"] = explain_role(role["title"])

        return recommendations
