"""
High-level job-related operations.

This module exists to keep job-board matching logic out of the resume upload
flow (`/parse-and-recommend`). The resume flow should focus on extracting a
resume and generating recommended roles; job matching can be triggered
separately via `/jobs/match`.
"""

from typing import Any

from app.services.job_matching_service import find_matching_jobs


def match_role_titles_to_jobs(
    role_titles: list[str],
    *,
    jobs_per_role: int = 10,
    include_company_jobs: bool = True,
    country: str = "us",
    candidate_skills: list[str] | None = None,
    candidate_level: str | None = None,
) -> dict[str, Any]:
    if not role_titles:
        return {"by_role": {}, "sources_used": []}

    roles = [{"title": t} for t in role_titles if t and t.strip()]
    return find_matching_jobs(
        roles,
        jobs_per_role=jobs_per_role,
        include_company_jobs=include_company_jobs,
        country=country,
        candidate_skills=candidate_skills,
        candidate_level=candidate_level,
    )

