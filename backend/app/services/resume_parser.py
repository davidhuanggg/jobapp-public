from fastapi import UploadFile
from io import BytesIO
from typing import Dict, List
import re

from docx import Document
from PyPDF2 import PdfReader

def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    text = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text.append(page_text)
    return "\n".join(text)


def extract_text_from_docx(file_bytes: bytes) -> str:
    doc = Document(BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs)

KNOWN_SKILLS = {
    "python", "java", "c++", "javascript", "typescript",
    "sql", "postgresql", "mysql", "mongodb",
    "machine learning", "deep learning", "nlp",
    "fastapi", "flask", "django",
    "react", "node", "docker", "kubernetes",
    "aws", "gcp", "azure", "linux", "git"
}

def extract_skills(text: str) -> list[str]:
    """
    Extract skills from resume text using simple heuristics.
    Looks for lines containing 'skills', bullets, or common skill keywords.
    """
    skills = []

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        # Look for "Skills" header
        if "skill" in line.lower():
            # grab next line(s) if colon is missing
            if ":" in line:
                parts = line.split(":")
                skills += [s.strip() for s in parts[1].split(",") if s.strip()]
            elif i + 1 < len(lines):
                skills += [s.strip() for s in lines[i + 1].split(",") if s.strip()]
        # Optional: match common skill keywords
        for keyword in ["python", "java", "sql", "machine learning", "c++"]:
            if keyword.lower() in line.lower() and keyword.lower() not in [s.lower() for s in skills]:
                skills.append(keyword)
    return skills

def extract_education(text: str) -> list[dict]:
    education = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if any(k in line.lower() for k in ["bachelor", "master", "university", "college"]):
            education.append({"degree": line, "field": "", "university": line})
    return education

def extract_work_experience(text: str) -> list[dict]:
    work_exp = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if any(k in line.lower() for k in ["company", "position", "intern", "engineer"]):
            work_exp.append({"company": line, "position": "", "duration": ""})
    return work_exp

