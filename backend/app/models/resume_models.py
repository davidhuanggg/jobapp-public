from pydantic import BaseModel
from typing import List, Dict, Optional

class CandidateContact(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None

class CandidateEducation(BaseModel):
    degree: Optional[str] = None
    field: Optional[str] = None
    university: Optional[str] = None

class WorkExperience(BaseModel):
    company: Optional[str] = None
    position: Optional[str] = None
    duration: Optional[str] = None

class Resume(BaseModel):
    name: Optional[str] = None
    contact: Optional[CandidateContact] = None
    education: Optional[CandidateEducation] = None
    work_experience: List[WorkExperience] = []
    skills: List[str] = []

class RecommendedRole(BaseModel):
    title: str
    reason: str
    detailed_explanation: Optional[str] = None
    learning_path: Optional[List[Dict]] = []

class RecommendationResponse(BaseModel):
    recommended_roles: List[RecommendedRole]

