import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup

GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs"

SKILL_KEYWORDS = {
    "python", "java", "javascript", "typescript",
    "react", "node", "django", "flask",
    "aws", "gcp", "azure", "docker", "kubernetes",
    "sql", "postgres", "mysql", "redis"
}

def fetch_greenhouse_jobs(company: str):
    url = GREENHOUSE_API.format(company=company)
    response = requests.get(url)
    response.raise_for_status()
    return response.json()["jobs"]

def extract_seniority(title: str):
    title = title.lower()
    if "intern" in title:
        return "intern"
    if "junior" in title:
        return "junior"
    if "senior" in title or "sr" in title:
        return "senior"
    if "staff" in title or "principal" in title:
        return "staff"
    return "mid"

def normalize_title(title: str):
    title = title.lower()
    if "backend" in title:
        return "Backend Software Engineer"
    if "frontend" in title or "front end" in title:
        return "Frontend Software Engineer"
    if "full stack" in title:
        return "Full Stack Software Engineer"
    if "machine learning" in title or "ml" in title:
        return "Machine Learning Engineer"
    return title.title()

def extract_skills(html_description: str):
    soup = BeautifulSoup(html_description, "html.parser")
    text = soup.get_text(" ").lower()
    return sorted(skill for skill in SKILL_KEYWORDS if skill in text)

def normalize_job(raw_job: dict, company: str):
    html_description = raw_job.get("content", "")
    location_name = raw_job.get("location", {}).get("name", "Unknown")
    source_url = raw_job.get("absolute_url", "")

    title = raw_job.get("title", "Unknown Title")

    return {
        "job_id": f"greenhouse_{company}_{raw_job['id']}",
        "company": company,
        "title": title,
        "normalized_title": normalize_title(title),
        "seniority": extract_seniority(title),
        "location": location_name,
        "remote_type": "remote" if "remote" in location_name.lower() else "onsite",
        "date_posted": raw_job.get("created_at"),
        "last_updated": raw_job.get("updated_at"),
        "required_skills": extract_skills(html_description),
        "ats_type": "greenhouse",
        "source_url": source_url,
        "raw_description": BeautifulSoup(html_description, "html.parser").get_text(" ")

    }

def ingest_company(company: str):
    raw_jobs = fetch_greenhouse_jobs(company)
    normalized_jobs = [
        normalize_job(job, company) for job in raw_jobs
    ]
    return normalized_jobs
