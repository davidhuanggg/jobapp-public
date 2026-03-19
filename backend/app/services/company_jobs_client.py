"""
Fetches job postings from official company career pages (Greenhouse, Lever).
Uses a configurable list of companies so we can match recommendations to real postings.
"""
from typing import Any

from app.services.job_ingestion_service import ingest_company_jobs


# Companies to check on official boards. Format: (company_slug, ats_type).
# Add more (company, "greenhouse"|"lever") as needed.
DEFAULT_COMPANIES: list[tuple[str, str]] = [
    ("stripe", "greenhouse"),
    ("notion", "greenhouse"),
    ("figma", "greenhouse"),
    ("linear", "lever"),
    ("vercel", "lever"),
    ("openai", "greenhouse"),
    ("anthropic", "greenhouse"),
    ("dropbox", "greenhouse"),
    ("asana", "greenhouse"),
    ("airtable", "greenhouse"),
]


def _normalize_company_job(raw: dict) -> dict[str, Any]:
    """Convert ingestor output to the same shape as job board client for matching."""
    return {
        "job_id": raw.get("job_id", ""),
        "company": raw.get("company", ""),
        "title": raw.get("title", ""),
        "location": raw.get("location", "Unknown"),
        "source": "company_careers",
        "ats_type": raw.get("ats_type", ""),
        "source_url": raw.get("source_url"),
        "description_snippet": "",
        "posted_date": raw.get("posting_date"),
        "required_skills": raw.get("required_skills", []),
    }


def fetch_company_jobs(
    companies: list[tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch jobs from official company career pages (Greenhouse/Lever).
    If companies is None, uses DEFAULT_COMPANIES. Each tuple is (company_slug, "greenhouse"|"lever").
    Returns normalized jobs; skips companies that fail (no network errors thrown).
    """
    to_fetch = companies or DEFAULT_COMPANIES
    out: list[dict[str, Any]] = []

    for company_slug, source in to_fetch:
        try:
            jobs = ingest_company_jobs(company_slug, source)
            out.extend(_normalize_company_job(j) for j in jobs)
        except Exception:
            continue

    return out
