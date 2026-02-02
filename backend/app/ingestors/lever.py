import requests
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

# ============================
# LEVER API
# ============================
LEVER_API = "https://api.lever.co/v0/postings/{company}?mode=json"

# ============================
# SKILL VOCABULARY
# (shared across ingestors)
# ============================
SKILL_KEYWORDS = {
    "python", "java", "javascript", "typescript",
    "react", "node", "django", "flask",
    "aws", "gcp", "azure", "docker", "kubernetes",
    "sql", "postgres", "mysql", "redis",
    "pandas", "numpy", "spark", "airflow",
    "machine learning", "deep learning", "nlp"
}

# ============================
# FETCH
# ============================
def fetch_lever_jobs(company: str) -> List[Dict]:
    """
    Fetch raw job postings from Lever API.
    """
    url = LEVER_API.format(company=company)
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()

    data = resp.json()
    return data if isinstance(data, list) else []

# ============================
# HELPERS
# ============================
def extract_text(html: Optional[str]) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    return soup.get_text(" ").lower()


def extract_skills(text: str) -> List[str]:
    """
    Extract known skills from job description text.
    """
    return sorted(skill for skill in SKILL_KEYWORDS if skill in text)


def extract_seniority(title: str) -> str:
    """
    Infer seniority from job title.
    """
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
    """
    Normalize job titles across companies.
    """
    t = title.lower()
    if "backend" in t:
        return "Backend Software Engineer"
    if "frontend" in t or "front end" in t:
        return "Frontend Software Engineer"
    if "full stack" in t:
        return "Full Stack Software Engineer"
    if "machine learning" in t or "ml" in t:
        return "Machine Learning Engineer"
    if "data engineer" in t:
        return "Data Engineer"
    if "data scientist" in t:
        return "Data Scientist"
    return "Software Engineer"


def parse_lever_date(ts: Optional[int]) -> Optional[str]:
    """
    Convert Lever epoch ms → ISO date string.
    """
    if not ts:
        return None
    return datetime.utcfromtimestamp(ts / 1000).date().isoformat()

# ============================
# NORMALIZATION
# ============================
def normalize_lever_job(job: Dict, company: str) -> Dict:
    """
    Normalize Lever job into platform-wide schema.
    """
    description_text = extract_text(job.get("description"))

    title = job.get("text", "Unknown Title")
    location = job.get("categories", {}).get("location", "Unknown")

    return {
        "job_id": f"lever_{job.get('id')}",
        "company": company,
        "title": title,
        "normalized_title": normalize_title(title),
        "seniority": extract_seniority(title),
        "location": location,
        "remote_type": (
            "remote"
            if "remote" in (job.get("workplaceType") or "").lower()
            else "onsite"
        ),
        "posting_date": parse_lever_date(job.get("createdAt")),
        "required_skills": extract_skills(description_text),
        "ats_type": "lever",
        "source_url": job.get("hostedUrl"),
    }

# ============================
# INGEST ENTRYPOINT
# ============================
def ingest_company(company: str) -> List[Dict]:
    """
    Ingest and normalize all active Lever jobs for a company.
    """
    raw_jobs = fetch_lever_jobs(company)
    return [normalize_lever_job(job, company) for job in raw_jobs]

