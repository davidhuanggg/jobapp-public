from sqlalchemy import Column, Integer, String, JSON, Date, UniqueConstraint
from app.db.database import Base

class JobPosting(Base):
    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True, index=True)

    job_id = Column(String, index=True)
    company = Column(String, index=True)

    title = Column(String)
    normalized_title = Column(String)
    seniority = Column(String)

    location = Column(String)
    remote_type = Column(String)

    posting_date = Column(String)

    required_skills = Column(JSON)

    ats_type = Column(String)
    source_url = Column(String)

    __table_args__ = (
        UniqueConstraint("job_id", name="unique_job_id"),
    )

