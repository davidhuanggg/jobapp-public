from collections import Counter
from sqlalchemy.orm import Session
from app.db.models import Job

def get_skill_frequency(db: Session):
    jobs = db.query(Job).all()

    skill_counter = Counter()

    for job in jobs:
        if job.skills:
            skill_counter.update([skill.lower() for skill in job.skills])

    return dict(skill_counter)
