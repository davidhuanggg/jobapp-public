from fastapi import APIRouter
from app.services.analytics_service import get_skill_frequency

router = APIRouter()

@router.get("/skills/frequency")
def skill_frequency():
    return get_skill_frequency()

