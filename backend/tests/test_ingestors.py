import responses
from collections import Counter

from app.ingestors import lever, greenhouse


# -----------------------------
@responses.activate
def test_lever_ingestor_basic():
    company = "testco"

    responses.add(
        responses.GET,
        f"https://api.lever.co/v0/postings/{company}?mode=json",
        json=[
            {
                "id": "123",
                "text": "Software Engineer",
                "description": "<p>Python, SQL, AWS</p>",
                "categories": {"location": "Remote"},
                "workplaceType": "remote",
                "createdAt": "2024-02-01",
                "hostedUrl": "https://jobs.lever.co/testco/123"
            }
        ],
        status=200,
    )

    jobs = lever.ingest_company(company)

    assert len(jobs) == 1
    job = jobs[0]
    assert job["company"] == company
    assert job["ats_type"] == "lever"
    assert "python" in job["required_skills"]


# -----------------------------------
@responses.activate
def test_lever_date_timestamp_normalization():
    company = "testco"

    responses.add(
        responses.GET,
        f"https://api.lever.co/v0/postings/{company}?mode=json",
        json=[
            {
                "id": "456",
                "text": "Backend Engineer",
                "description": "<p>Go, Docker</p>",
                "categories": {"location": "NY"},
                "workplaceType": "onsite",
                "createdAt": 1706745600000,  # timestamp
                "hostedUrl": "url"
            }
        ],
        status=200,
    )

    jobs = lever.ingest_company(company)
    assert jobs[0]["posting_date"] == "2024-02-01"


# --------------------------------
@responses.activate
def test_skill_frequency_lever():
    company = "testco"

    responses.add(
        responses.GET,
        f"https://api.lever.co/v0/postings/{company}?mode=json",
        json=[
            {
                "id": "1",
                "text": "Backend Engineer",
                "description": "<p>Python, AWS</p>",
                "categories": {"location": "NY"},
                "workplaceType": "onsite",
                "createdAt": "2024-02-01",
                "hostedUrl": "url1",
            },
            {
                "id": "2",
                "text": "Data Engineer",
                "description": "<p>Python, SQL, AWS</p>",
                "categories": {"location": "NY"},
                "workplaceType": "onsite",
                "createdAt": "2024-02-02",
                "hostedUrl": "url2",
            },
        ],
        status=200,
    )

    jobs = lever.ingest_company(company)
    skills = [s for job in jobs for s in job["required_skills"]]
    freq = Counter(skills)

    assert freq["python"] == 2
    assert freq["aws"] == 2
    assert freq["sql"] == 1


# -------------------------------
@responses.activate
def test_greenhouse_ingestor_basic():
    company = "testco"

    responses.add(
        responses.GET,
        f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs",
        json={
            "jobs": [
                {
                    "id": 1,
                    "title": "Software Engineer",
                    "content": "<p>Python, Docker</p>",
                    "location": {"name": "Remote"},
                    "updated_at": "2024-02-01",
                    "absolute_url": "url",
                }
            ]
        },
        status=200,
    )

    jobs = greenhouse.ingest_company(company)

    assert len(jobs) == 1
    job = jobs[0]
    assert job["ats_type"] == "greenhouse"
    assert "python" in job["required_skills"]


# ----------------------------------
@responses.activate
def test_skill_frequency_greenhouse():
    company = "testco"

    responses.add(
        responses.GET,
        f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs",
        json={
            "jobs": [
                {
                    "id": 1,
                    "title": "Backend Engineer",
                    "content": "<p>Python, AWS</p>",
                    "location": {"name": "Remote"},
                    "updated_at": "2024-02-01",
                    "absolute_url": "url1",
                },
                {
                    "id": 2,
                    "title": "Data Engineer",
                    "content": "<p>Python, SQL</p>",
                    "location": {"name": "Remote"},
                    "updated_at": "2024-02-02",
                    "absolute_url": "url2",
                },
            ]
        },
        status=200,
    )

    jobs = greenhouse.ingest_company(company)
    skills = [s for job in jobs for s in job["required_skills"]]
    freq = Counter(skills)

    assert freq["python"] == 2
    assert freq["aws"] == 1
    assert freq["sql"] == 1


# ----------------------------------
@responses.activate
def test_ingestor_empty_response():
    company = "emptyco"

    responses.add(
        responses.GET,
        f"https://api.lever.co/v0/postings/{company}?mode=json",
        json=[],
        status=200,
    )

    jobs = lever.ingest_company(company)
    assert jobs == []
