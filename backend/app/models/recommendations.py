from pydantic import BaseModel
from typing import List

class RecommendedRole(BaseModel):
    title: str
    reason: str
    detailed_explanation: dict | None = None

class LearningPathItem(BaseModel):
    skill: str
    courses: List[str]

class RecommendationResponse(BaseModel):
    recommended_roles: List[RecommendedRole]
    learning_paths: List[LearningPathItem]

