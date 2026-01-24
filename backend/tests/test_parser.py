import pytest
from app.services.extractor_service import extract_resume_data

def test_parse_pdf_resume():
    resume = extract_resume_data("tests/fixtures/sample_resume.pdf")
    assert isinstance(resume.skills, list)
    assert isinstance(resume.education, dict)
    assert len(resume.skills) > 0

def test_parse_docx_resume():
    resume = extract_resume_data("tests/fixtures/sample_resume.docx")
    assert isinstance(resume.skills, list)
    assert isinstance(resume.education, dict)
    assert len(resume.skills) > 0

def test_parse_invalid_file():
    with pytest.raises(Exception):
        extract_resume_data("tests/fixtures/invalid_file.txt")

