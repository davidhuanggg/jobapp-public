import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_parse_resume_endpoint_success():
    with open("tests/fixtures/sample_resume.pdf", "rb") as f:
        response = client.post("/parse-resume", files={"file": ("resume.pdf", f, "application/pdf")})
    assert response.status_code == 200
    data = response.json()
    assert "skills" in data
    assert "education" in data

def test_parse_resume_endpoint_no_file():
    response = client.post("/parse-resume")
    assert response.status_code == 422  # FastAPI will reject missing file

def test_recommend_jobs_requires_resume():
    response = client.post("/recommend-jobs", json={})
    assert response.status_code == 400

