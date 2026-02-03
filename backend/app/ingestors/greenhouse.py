import requests
from datetime import datetime
from app.ingestors.utils import extract_skills_from_html

GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs"


def fetch_greenhouse_jobs(company: str) -> list[dict]:
    url = GREENHOUSE_API.format(company=company)
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json().get("jobs", [])


def extract_seniority(title: str) -> str:
    t = title.lower()
    if "intern" in t:
        return "intern"
    if "junior" in t:
        return "junior"
    if "senior" in t or "sr" in t:
        return "senior"
    if "staff" in t or "principal" in t:
        return "staff"
    return "mid"


def normalize_title(title: str) -> str:
    t = title.lower()
    if "machine learning" in t:
        return "Machine Learning Engineer"
    if "data" in t:
        return "Data Engineer"
    if "frontend" in t:
        return "Frontend Engineer"
    if "backend" in t:
        return "Backend Engineer"
    return title


def normalize_greenhouse_job(raw: dict, company: str) -> dict:
    html = raw.get("content", "")
    location = raw.get("location", {}).get("name", "Unknown")

    return {
        "job_id": f"greenhouse_{raw['id']}",
        "company": company,
        "title": raw.get("title"),
        "normalized_title": normalize_title(raw.get("title", "")),
        "seniority": extract_seniority(raw.get("title", "")),
        "location": location,
        "remote_type": "remote" if "remote" in location.lower() else "onsite",
        "posting_date": raw.get("updated_at", "")[:10],
        "required_skills": extract_skills_from_html(html),
        "ats_type": "greenhouse",
        "source_url": raw.get("absolute_url"),
    }


def ingest_company(company: str) -> list[dict]:
    raw_jobs = fetch_greenhouse_jobs(company)
    return [normalize_greenhouse_job(j, company) for j in raw_jobs]

