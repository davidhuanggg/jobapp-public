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
    text_lower = text.lower()
    found = set()

    for skill in KNOWN_SKILLS:
        if re.search(rf"\b{re.escape(skill)}\b", text_lower):
            found.add(skill)

    return sorted(found)

def extract_education(text: str) -> dict:
    text_lower = text.lower()

    degree_patterns = {
        "bachelor": r"(b\.?s\.?|bachelor)",
        "master": r"(m\.?s\.?|master)",
        "phd": r"(ph\.?d|doctorate)"
    }

    for degree, pattern in degree_patterns.items():
        if re.search(pattern, text_lower):
            return {"degree": degree.title()}

    return {}

def extract_work_experience(text: str) -> list[dict]:
    experience = []

    lines = text.splitlines()
    for line in lines:
        if any(word in line.lower() for word in ["engineer", "developer", "intern"]):
            experience.append({"title": line.strip()})

    return experience[:5]
