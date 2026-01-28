from sqlalchemy import Column, Integer, Text, JSON
from app.db.database import Base

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    raw_text = Column(Text, nullable=False)

    skills = Column(JSON, nullable=True)
    education = Column(JSON, nullable=True)
    work_experience = Column(JSON, nullable=True)
