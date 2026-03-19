"""
Fetches job postings from official company career pages (Greenhouse, Lever).

To avoid a manual "companies" list, we can auto-discover ATS tokens (Greenhouse
board token / Lever company token) by parsing those tokens out of the job
application URLs returned by job-board APIs.

If auto-discovery yields nothing, we fall back to a small default list.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.job_ingestion_service import ingest_company_jobs


# Fallback companies to check on official boards. Format: (company_slug, ats_type).
# This is only used when ATS-token discovery yields nothing.
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


def _extract_greenhouse_board_token(url: str) -> str | None:
    """
    Examples:
    - https://boards.greenhouse.io/stripe/jobs/123
    - https://jobs.greenhouse.io/stripe/jobs/123
    """
    if not url:
        return None
    m = re.search(r"(?:boards\.greenhouse\.io|jobs\.greenhouse\.io)/([^/]+)/jobs", url)
    if not m:
        return None
    token = (m.group(1) or "").strip()
    return token or None


def _extract_lever_company_token(url: str) -> str | None:
    """
    Examples:
    - https://jobs.lever.co/linear/abc123
    - https://linear.lever.co/abc123
    """
    if not url:
        return None

    m = re.search(r"jobs\.lever\.co/([^/]+)/", url)
    if m:
        token = (m.group(1) or "").strip()
        if token:
            return token

    m2 = re.search(r"//([^/]+)\.lever\.co/", url)
    if m2:
        token = (m2.group(1) or "").strip()
        if token:
            return token

    return None


def discover_company_tokens_from_urls(urls: list[str]) -> list[tuple[str, str]]:
    """
    Discover (company_slug, ats_type) tuples by parsing ATS tokens from URLs.
    """
    discovered: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for url in urls:
        gh = _extract_greenhouse_board_token(url)
        if gh:
            tup = (gh, "greenhouse")
            if tup not in seen:
                discovered.append(tup)
                seen.add(tup)
            continue

        lever = _extract_lever_company_token(url)
        if lever:
            tup = (lever, "lever")
            if tup not in seen:
                discovered.append(tup)
                seen.add(tup)
            continue

    return discovered


def fetch_company_jobs(
    companies: list[tuple[str, str]] | None = None,
    urls: list[str] | None = None,
    max_boards: int = 20,
) -> list[dict[str, Any]]:
    """
    Fetch jobs from official company career pages (Greenhouse/Lever).

    - If `companies` is provided, use that list.
    - Else, if `urls` is provided, auto-discover ATS tokens from those URLs and
      fetch official postings for the discovered boards/companies.
    - Else, fall back to DEFAULT_COMPANIES.

    Each tuple is (company_slug, "greenhouse"|"lever").
    """
    if companies:
        to_fetch = companies
    elif urls:
        discovered = discover_company_tokens_from_urls(urls)
        to_fetch = discovered[:max_boards] if discovered else DEFAULT_COMPANIES
    else:
        to_fetch = DEFAULT_COMPANIES

    out: list[dict[str, Any]] = []

    for company_slug, source in to_fetch:
        try:
            jobs = ingest_company_jobs(company_slug, source)
            out.extend(_normalize_company_job(j) for j in jobs)
        except Exception:
            continue

    return out
