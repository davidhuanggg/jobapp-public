"""
Job board API clients. Returns jobs in a normalized shape for matching to recommendations.

Providers:
- Adzuna: Free API key, single aggregator. Good default.
- JSearch (RapidAPI): Aggregates LinkedIn, Indeed, Glassdoor, ZipRecruiter, etc.;
  free tier ~200 req/mo, then paid. Best coverage.

Greenhouse/Lever: Used for *official company career pages* (per-company), not global
search — see company_jobs_client.py. "Greenboard" = Greenhouse job board = already
integrated there.
"""
import logging
import os
from typing import Any

import requests
from dotenv import load_dotenv
from pathlib import Path

_log = logging.getLogger(__name__)

# Load .env files by absolute path so launch CWD doesn't matter.
# services/.env holds Adzuna/RapidAPI keys; backend/.env holds shared keys (GROQ, etc.).
_here = Path(__file__).resolve().parent
load_dotenv(dotenv_path=_here / ".env", override=False)                  # app/services/.env
load_dotenv(dotenv_path=_here.parent.parent / ".env", override=False)    # backend/.env

# ---------------------------------------------------------------------------
# Normalized job shape (all providers map to this)
# ---------------------------------------------------------------------------
def _normalized_job(
    job_id: str,
    company: str,
    title: str,
    location: str,
    source: str,
    source_url: str | None = None,
    description_snippet: str = "",
    salary_min: int | None = None,
    salary_max: int | None = None,
    posted_date: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "job_id": job_id,
        "company": company,
        "title": title,
        "location": location,
        "source": source,
        "source_url": source_url,
        # Longer text so resume-vs-job matching can see skills (UI may still truncate).
        "description_snippet": (description_snippet or "")[:12000],
        "salary_min": salary_min,
        "salary_max": salary_max,
        "posted_date": posted_date,
    }
    out.update({k: v for k, v in extra.items() if v is not None})
    return out


# ---------------------------------------------------------------------------
# Adzuna
# ---------------------------------------------------------------------------
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
ADZUNA_COUNTRY = os.getenv("ADZUNA_COUNTRY", "us").lower()
ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"


def _search_adzuna(
    query: str,
    country: str | None = None,
    results_per_page: int = 20,
    page: int = 1,
) -> list[dict[str, Any]]:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        return []
    country = (country or ADZUNA_COUNTRY).lower()
    url = f"{ADZUNA_BASE}/{country}/search/{page}"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": query.strip(),
        "results_per_page": min(results_per_page, 50),
        "content-type": "application/json",
    }
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        results = (resp.json() or {}).get("results") or []
    except Exception as exc:
        _log.warning("Adzuna request failed for query=%r: %s", query, exc)
        return []
    out = []
    for j in results:
        loc = j.get("location") or {}
        display_location = loc.get("display_name", "Unknown") if isinstance(loc, dict) else "Unknown"
        company = j.get("company") or {}
        company_name = company.get("display_name", "Unknown") if isinstance(company, dict) else "Unknown"
        created = (j.get("created") or "")[:10] if j.get("created") else None
        out.append(
            _normalized_job(
                job_id=f"adzuna_{j.get('id', '')}",
                company=company_name,
                title=j.get("title", ""),
                location=display_location,
                source="adzuna",
                source_url=j.get("redirect_url"),
                description_snippet=(j.get("description") or "")[:12000],
                salary_min=j.get("salary_min"),
                salary_max=j.get("salary_max"),
                posted_date=created,
            )
        )
    _log.info("Adzuna query=%r  returned=%d jobs (raw results=%d)", query, len(out), len(results))
    return out


# ---------------------------------------------------------------------------
# JSearch (RapidAPI) — LinkedIn, Indeed, Glassdoor, ZipRecruiter, etc.
# ---------------------------------------------------------------------------
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
JSEARCH_HOST = "jsearch.p.rapidapi.com"
JSEARCH_URL = f"https://{JSEARCH_HOST}/search"


def _search_jsearch(
    query: str,
    country: str | None = None,
    page: int = 1,
    num_pages: int = 1,
) -> list[dict[str, Any]]:
    if not RAPIDAPI_KEY:
        return []
    params = {
        "query": query.strip(),
        "page": str(page),
        "num_pages": str(num_pages),
        "date_posted": "week",   # pre-filter at source; our local 3-day window refines further
    }
    if country:
        # JSearch expects country code (e.g. "us")
        params["country"] = country.strip().lower()
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": JSEARCH_HOST,
    }
    try:
        resp = requests.get(JSEARCH_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json() or {}
        results = data.get("data") or []
    except Exception as exc:
        _log.warning("JSearch request failed for query=%r: %s", query, exc)
        return []
    out = []
    for j in results:
        emp = j.get("employer_name") or "Unknown"
        city = j.get("job_city") or ""
        country = j.get("job_country") or ""
        location = ", ".join(filter(None, [city, country])) or "Unknown"

        job_id = j.get("job_id") or j.get("job_apply_link") or ""

        # Structured skills list — this is the primary signal for requirement matching.
        raw_skills = j.get("job_required_skills") or []
        required_skills = [s for s in raw_skills if isinstance(s, str) and s.strip()] or None

        # Pull key highlights out of job_highlights if present.
        highlights = j.get("job_highlights") or {}
        qualifications = highlights.get("Qualifications") or []
        responsibilities = highlights.get("Responsibilities") or []

        out.append(
            _normalized_job(
                job_id=f"jsearch_{job_id[:80]}" if job_id else "",
                company=emp,
                title=j.get("job_title", ""),
                location=location,
                source="jsearch",
                source_url=j.get("job_apply_link") or j.get("job_apply_redirect_url"),
                description_snippet=(j.get("job_description") or "")[:12000],
                salary_min=j.get("job_min_salary"),
                salary_max=j.get("job_max_salary"),
                posted_date=(j.get("job_posted_at_datetime_utc") or "")[:10] if j.get("job_posted_at_datetime_utc") else None,
                # JSearch-specific enrichment fields
                required_skills=required_skills,
                employment_type=j.get("job_employment_type"),
                is_remote=j.get("job_is_remote"),
                qualifications=qualifications if qualifications else None,
                responsibilities=responsibilities if responsibilities else None,
            )
        )
    _log.info("JSearch query=%r  returned=%d jobs (raw results=%d)", query, len(out), len(results))
    return out


# ---------------------------------------------------------------------------
# Provider selection and unified search
# ---------------------------------------------------------------------------
def _enabled_providers() -> list[str]:
    """Which job board API providers have credentials set."""
    out = []
    if ADZUNA_APP_ID and ADZUNA_APP_KEY:
        out.append("adzuna")
    if RAPIDAPI_KEY:
        out.append("jsearch")
    return out


def search_jobs(
    query: str,
    country: str | None = None,
    results_per_page: int = 20,
    page: int = 1,
    providers: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Search job boards by keyword (e.g. job title). Uses all enabled providers
    (Adzuna, JSearch) and merges results. Dedupes by job_id.

    Optional: set ADZUNA_APP_ID + ADZUNA_APP_KEY and/or RAPIDAPI_KEY in .env.
    If providers is set (e.g. ["adzuna"]), only those are used; otherwise all enabled.
    """
    to_use = providers or _enabled_providers()
    if not to_use:
        return []

    all_jobs: list[dict[str, Any]] = []
    if "adzuna" in to_use:
        all_jobs.extend(
            _search_adzuna(query, country=country, results_per_page=results_per_page, page=page)
        )
    if "jsearch" in to_use:
        all_jobs.extend(_search_jsearch(query, country=country, page=page, num_pages=1))

    # Dedupe by (source, job_id) then by source_url as fallback
    seen: set[str] = set()
    unique = []
    for j in all_jobs:
        key = j.get("job_id") or j.get("source_url") or ""
        if key and key not in seen:
            seen.add(key)
            unique.append(j)
        elif not key:
            unique.append(j)
    return unique
