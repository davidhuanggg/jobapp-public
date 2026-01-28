from sqlalchemy import Column, Integer, Text
from app.db.database import Base

class ResumeDB(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    raw_text = Column(Text, nullable=False)

