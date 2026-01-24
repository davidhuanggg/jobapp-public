import re
from pathlib import Path
from typing import Dict
from pdfminer.high_level import extract_text as pdf_extract_text
from docx import Document

def extract_text(file_path: str) -> str:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return pdf_extract_text(file_path)
    elif suffix in [".doc", ".docx"]:
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def split_sections(text: str) -> Dict[str, str]:
    sections = {}
    headers = ["skills", "experience", "education", "projects", "certifications"]
    current_header = None
    buffer = []

    for line in text.splitlines():
        line_lower = line.strip().lower()
        if line_lower in headers:
            if current_header:
                sections[current_header] = "\n".join(buffer).strip()
            current_header = line_lower
            buffer = []
        elif current_header:
            buffer.append(line)
    if current_header:
        sections[current_header] = "\n".join(buffer).strip()
    return sections

def extract_contact(text: str) -> Dict[str, str]:
    email_match = re.search(r"[\w\.-]+@[\w\.-]+", text)
    phone_match = re.search(r"\+?\d[\d\s\-\(\)]{7,}\d", text)
    return {
        "email": email_match.group(0) if email_match else "",
        "phone": phone_match.group(0) if phone_match else ""
    }

def extract_skills(text: str) -> list[str]:
    possible_skills = ["Python", "Java", "SQL", "Docker", "Kubernetes", "FastAPI", "React", "Node.js"]
    return [skill for skill in possible_skills if skill.lower() in text.lower()]

def extract_name(text: str) -> str | None:
    for line in text.splitlines():
        words = line.strip().split()
        if len(words) >= 2 and all(w.istitle() for w in words[:2]):
            return " ".join(words[:2])
    return None

