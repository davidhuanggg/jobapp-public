"""
Matches recommended roles to real job postings from job board APIs and official company career pages.
"""
import re
from typing import Any

from app.services.job_board_client import search_jobs as job_board_search
from app.services.company_jobs_client import fetch_company_jobs
from app.services.requirement_match_service import resume_to_job_match_stats


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
        for j in jobs:
            # Tighten matching: avoid "Backend Engineer" matching "Software Engineer".
            job_title = j.get("title") or ""
            if not _title_overlap(title, job_title):
                continue

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

    # If we have resume skills: attach requirement_match_pct, drop 0%, sort high → low.
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
            positive = [j for j in jobs_list if j.get("requirement_match_pct", 0) > 0]
            by_role[title] = positive[:jobs_per_role]

    return {"by_role": by_role, "sources_used": list(dict.fromkeys(sources_used))}
