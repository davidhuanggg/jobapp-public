import tempfile
import os
from fastapi import UploadFile
from typing import Dict, List
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document
import re


async def extract_resume_data(file: UploadFile) -> Dict:
    """
    Fully async extractor that returns structured resume JSON:
    {
        name: str,
        contact: {email: str, phone: str},
        skills: List[str],
        education: List[dict],
        work_experience: List[dict],
        raw_text: str
    }
    """
    suffix = os.path.splitext(file.filename)[1] or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    raw_text = ""
    try:
        if suffix.lower() == ".pdf":
            raw_text = extract_pdf_text(tmp_path)
        elif suffix.lower() == ".docx":
            doc = Document(tmp_path)
            raw_text = "\n".join([p.text for p in doc.paragraphs])
        else:
            raw_text = open(tmp_path, "r", encoding="utf-8", errors="ignore").read()
    finally:
        os.remove(tmp_path)

    parsed_resume = {
        "name": extract_name(raw_text),
        "contact": extract_contact(raw_text),
        "skills": extract_skills(raw_text),
        "education": extract_education(raw_text),
        "work_experience": extract_work_experience(raw_text),
        "raw_text": raw_text
    }

    return parsed_resume


# -------------------------
# Helper extraction functions
# -------------------------

def extract_name(text: str) -> str:
    """Simple heuristic: first non-empty line, possibly all caps"""
    for line in text.splitlines():
        line = line.strip()
        if line and len(line.split()) <= 5:  # assume name is short
            return line
    return "Unknown"


def extract_contact(text: str) -> dict:
    """Extract email and phone using regex"""
    email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}", text)
    return {
        "email": email_match.group(0) if email_match else "",
        "phone": phone_match.group(0) if phone_match else ""
    }


def extract_skills(text: str) -> List[str]:
    """Extract skills using heuristics and common skill keywords"""
    skills = set()
    common_skills = [
        "python", "java", "sql", "c++", "c#", "javascript", "typescript", "machine learning",
        "deep learning", "pandas", "numpy", "tensorflow", "pytorch", "fastapi", "flask"
    ]
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        # Look for "Skills" section
        if "skill" in line.lower():
            if ":" in line:
                parts = line.split(":")
                for s in parts[1].split(","):
                    if s.strip():
                        skills.add(s.strip())
            elif i + 1 < len(lines):
                for s in lines[i + 1].split(","):
                    if s.strip():
                        skills.add(s.strip())
        # Look for keywords anywhere
        for kw in common_skills:
            if kw.lower() in line.lower():
                skills.add(kw)
    return list(skills)


def extract_education(text: str) -> List[dict]:
    """Extract education entries by looking for degrees/universities"""
    education = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if any(k in line.lower() for k in ["bachelor", "master", "university", "college", "phd"]):
            education.append({
                "degree": line,
                "field": "",  # optional
                "university": line
            })
    return education


def extract_work_experience(text: str) -> List[dict]:
    """Extract work experience by looking for company/job keywords"""
    work_exp = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if any(k in line.lower() for k in ["company", "position", "intern", "engineer", "developer", "analyst"]):
            work_exp.append({
                "company": line,
                "position": "",
                "duration": ""
            })
    return work_exp

