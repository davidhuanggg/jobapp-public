"""
Matches recommended roles to real job postings from job board APIs and official company career pages.
"""
import re
from typing import Any

from app.services.job_board_client import search_jobs as job_board_search
from app.services.company_jobs_client import fetch_company_jobs


def _normalize_for_match(text: str) -> str:
    return re.sub(r"[^\w\s]", "", (text or "").lower()).strip()


def _title_overlap(recommended_title: str, job_title: str) -> bool:
    """True if the recommended title and job title share meaningful overlap."""
    r = _normalize_for_match(recommended_title)
    j = _normalize_for_match(job_title)
    if not r or not j:
        return False
    # Exact or contained
    if r in j or j in r:
        return True
    # Shared significant words (length > 2)
    r_words = {w for w in r.split() if len(w) > 2}
    j_words = set(j.split())
    return bool(r_words & j_words)


def _match_company_jobs_to_roles(
    company_jobs: list[dict[str, Any]],
    role_titles: list[str],
) -> dict[str, list[dict[str, Any]]]:
    """For each role title, return company jobs whose title matches."""
    out: dict[str, list[dict[str, Any]]] = {t: [] for t in role_titles}
    for job in company_jobs:
        job_title = job.get("title") or ""
        for role_title in role_titles:
            if _title_overlap(role_title, job_title):
                out[role_title].append(job)
    return out


def find_matching_jobs(
    recommended_roles: list[dict[str, Any]],
    *,
    jobs_per_role: int = 10,
    include_company_jobs: bool = True,
    company_list: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """
    For each recommended role (dict with "title"), find matching real jobs from:
    - Job board APIs (Adzuna and/or JSearch if credentials set)
    - Official company career pages (Greenhouse/Lever)

    Returns:
    {
      "by_role": { "Recommended Role Title": [ job, ... ] },
      "sources_used": ["adzuna", "jsearch", "company_careers"]
    }
    """
    role_titles = [r.get("title", "").strip() for r in recommended_roles if r.get("title")]
    by_role: dict[str, list[dict[str, Any]]] = {t: [] for t in role_titles}
    sources_used: list[str] = []
    candidate_official_urls: set[str] = set()

    # Job board APIs: one search per role title (uses all enabled providers)
    for title in role_titles:
        jobs = job_board_search(query=title, results_per_page=jobs_per_role, country="us")
        for j in jobs:
            src = j.get("source")
            if src and src not in sources_used:
                sources_used.append(src)
            by_role[title].append(j)
            u = j.get("source_url") or ""
            if u:
                candidate_official_urls.add(u)

    # Official company career pages
    if include_company_jobs:
        company_jobs = fetch_company_jobs(
            companies=company_list,
            urls=list(candidate_official_urls),
            max_boards=20,
        )
        if company_jobs:
            sources_used.append("company_careers")
        matched = _match_company_jobs_to_roles(company_jobs, role_titles)
        for title, jobs in matched.items():
            by_role.setdefault(title, []).extend(jobs)

    # Dedupe by job_id per role
    for title in by_role:
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for j in by_role[title]:
            jid = j.get("job_id") or ""
            if jid and jid not in seen:
                seen.add(jid)
                unique.append(j)
            elif not jid:
                unique.append(j)
        by_role[title] = unique

    return {"by_role": by_role, "sources_used": list(dict.fromkeys(sources_used))}
