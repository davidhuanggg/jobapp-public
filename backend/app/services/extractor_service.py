import os
import tempfile
from fastapi import UploadFile
from .resume_parser import extract_text_from_pdf, extract_text_from_docx,extract_skills,extract_education,extract_work_experience

async def extract_resume_data(file: UploadFile) -> dict:
    contents = await file.read()

    if not contents:
        return None

    filename = file.filename.lower()

    if filename.endswith(".pdf"):
        raw_text = extract_text_from_pdf(contents)
    elif filename.endswith(".docx"):
        raw_text = extract_text_from_docx(contents)
    elif filename.endswith(".txt"):
        raw_text = contents.decode("utf-8", errors="ignore")
    else:
        raise ValueError("Unsupported file type")

    if not raw_text.strip():
        return None

    return {
        "raw_text": raw_text,
        "skills": extract_skills(raw_text),
        "education": extract_education(raw_text),
        "work_experience": extract_work_experience(raw_text),
    }

async def parse_resume_file(file: UploadFile):
    import os, tempfile
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    # Call your parsing logic
    resume_data = extract_resume_data(tmp_path)
    os.remove(tmp_path)
    return resume_data
