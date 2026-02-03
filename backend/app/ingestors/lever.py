import requests
from datetime import datetime
from app.ingestors.utils import extract_skills_from_html

LEVER_API = "https://api.lever.co/v0/postings/{company}?mode=json"


def fetch_lever_jobs(company: str) -> list[dict]:
    url = LEVER_API.format(company=company)
    resp = requests.get(url)
    resp.raise_for_status()

    data = resp.json()
    return data if isinstance(data, list) else []

def normalize_lever_date(created_at):
    if isinstance(created_at, int):
        return datetime.utcfromtimestamp(created_at / 1000).date().isoformat()
    if isinstance(created_at, str):
        return created_at[:10]
    return None

def extract_seniority(title: str) -> str:
    t = title.lower()
    if "intern" in t:
        return "intern"
    if "junior" in t:
        return "junior"
    if "senior" in t:
        return "senior"
    return "mid"


def normalize_lever_job(job: dict, company: str) -> dict:
    html = job.get("description", "")
    location = job.get("categories", {}).get("location", "Unknown")

    return {
        "job_id": f"lever_{job.get('id')}",
        "company": company,
        "title": job.get("text"),
        "normalized_title": job.get("text"),
        "seniority": extract_seniority(job.get("text", "")),
        "location": location,
        "remote_type": "remote" if "remote" in (job.get("workplaceType") or "").lower() else "onsite",
	"posting_date": normalize_lever_date(job.get("createdAt")),
        "required_skills": extract_skills_from_html(html),
        "ats_type": "lever",
        "source_url": job.get("hostedUrl"),
    }


def ingest_company(company: str) -> list[dict]:
    jobs = fetch_lever_jobs(company)
    return [normalize_lever_job(j, company) for j in jobs]

