from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.database import Base

class ResumeDB(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="")
    email = Column(String, default="")
    phone = Column(String, default="")
    raw_text = Column(Text, nullable=False)
    skills = Column(JSON, default=[])

    # Relationships
    education = relationship("EducationDB", back_populates="resume", cascade="all, delete-orphan")
    work_experience = relationship("WorkExperienceDB", back_populates="resume", cascade="all, delete-orphan")
#SHA-256 always produces 64 hex characters this line helps prevent duplication
    content_hash = Column(String(64), unique=True, nullable=False)

class EducationDB(Base):
    __tablename__ = "education"

    id = Column(Integer, primary_key=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    degree = Column(String, default="")
    field = Column(String, default="")
    university = Column(String, default="")

    resume = relationship("ResumeDB", back_populates="education")


class WorkExperienceDB(Base):
    __tablename__ = "work_experience"

    id = Column(Integer, primary_key=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    company = Column(String, default="")
    position = Column(String, default="")
    duration = Column(String, default="")

    resume = relationship("ResumeDB", back_populates="work_experience")

class JobRole(Base):
    __tablename__ = "job_roles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True, nullable=False)
    skills = Column(JSON, nullable=False)

class SkillGapResult(Base):
    __tablename__ = "skill_gaps"

    id = Column(Integer, primary_key=True)
    resume_id = Column(Integer, index=True)
    core_skills = Column(JSON)
    important_skills = Column(JSON)
    optional_skills = Column(JSON)
