"""
Matches recommended roles to real job postings from job board APIs and official company career pages.
"""
import logging
import re
from datetime import date, datetime, timezone
from typing import Any

from app.services.job_board_client import search_jobs as job_board_search

_log = logging.getLogger(__name__)
from app.services.company_jobs_client import fetch_company_jobs
from app.services.requirement_match_service import resume_to_job_match_stats
from app.services.experience_level_service import infer_job_level, level_compatible


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

    # Remove very generic title tokens so we don't match
    # "Backend Engineer" with "Software Engineer".
    title_stopwords = {
        "engineer",
        "developer",
        "analyst",
        "specialist",
        "manager",
        "lead",
        "architect",
        "staff",
        "principal",
        "sr",
        "jr",
        "junior",
        "senior",
    }

    r_tokens = [w for w in r.split() if w and w not in title_stopwords]
    j_tokens = set(j.split())

    # If we couldn't extract any domain-ish tokens, fall back to a looser overlap.
    if len(r_tokens) == 0:
        r_words = {w for w in r.split() if len(w) > 2}
        return bool(r_words & j_tokens)

    return bool(set(r_tokens) & j_tokens)


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
    country: str = "us",
    candidate_skills: list[str] | None = None,
    candidate_level: str | None = None,
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
        jobs = job_board_search(
            query=title,
            results_per_page=jobs_per_role,
            country=country,
        )
        passed, dropped = 0, 0
        for j in jobs:
            # Tighten matching: avoid "Backend Engineer" matching "Software Engineer".
            job_title = j.get("title") or ""
            if not _title_overlap(title, job_title):
                dropped += 1
                continue

            passed += 1
            src = j.get("source")
            if src and src not in sources_used:
                sources_used.append(src)
            by_role[title].append(j)
            u = j.get("source_url") or ""
            if u:
                candidate_official_urls.add(u)
        _log.info("Title=%r  raw=%d  passed_overlap=%d  dropped_overlap=%d", title, len(jobs), passed, dropped)

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

    # Dedupe by job_id per role, then drop stale listings (> 7 days old).
    # JSearch pre-filters to "week" at the API level; keep in sync here.
    _today = datetime.now(tz=timezone.utc).date()
    _MAX_DAYS = 7
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
        # Compute days_since_posted and drop listings older than _MAX_DAYS.
        fresh: list[dict[str, Any]] = []
        for j in unique:
            raw_date = j.get("posted_date")
            if raw_date:
                try:
                    posted = datetime.strptime(str(raw_date)[:10], "%Y-%m-%d").date()
                    days_ago = (_today - posted).days
                    j["days_since_posted"] = days_ago
                    if days_ago <= _MAX_DAYS:
                        fresh.append(j)
                except ValueError:
                    j["days_since_posted"] = None
                    fresh.append(j)   # unparseable date → keep
            else:
                j["days_since_posted"] = None
                fresh.append(j)       # no date info → keep
        by_role[title] = fresh

    # Attach job_level to every job (regardless of resume).
    for title in list(by_role.keys()):
        for job in by_role[title]:
            level, min_yoe = infer_job_level(
                job.get("description_snippet") or "",
                job.get("title") or "",
            )
            job["job_level"] = level
            if min_yoe is not None:
                job["job_min_yoe"] = min_yoe

    # Always apply level compatibility filter when we know the candidate's level.
    # This runs regardless of whether resume skills are present.
    if candidate_level:
        for title in list(by_role.keys()):
            by_role[title] = [
                j for j in by_role[title]
                if level_compatible(candidate_level, j.get("job_level"))
            ]

    # Score and sort by requirement match when resume skills are available.
    if candidate_skills:
        for title in list(by_role.keys()):
            jobs_list = by_role[title]
            for job in jobs_list:
                stats = resume_to_job_match_stats(candidate_skills, job)
                pct = stats.get("requirement_match_pct")
                for k in (
                    "requirement_match_ratio",
                    "skills_matched_count",
                    "job_skills_considered",
                    "has_requirements",
                    "match_basis",
                ):
                    job.pop(k, None)
                job["requirement_match_pct"] = 0 if pct is None else int(pct)

            jobs_list.sort(key=lambda j: j.get("requirement_match_pct", 0), reverse=True)
            by_role[title] = jobs_list[:jobs_per_role]

    return {"by_role": by_role, "sources_used": list(dict.fromkeys(sources_used))}
