"""
**Resume vs job listings** — compares saved resume skills to each job (inferred
signals from description + title, or explicit ``required_skills``). Used by
``/jobs/match`` when a resume is provided.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.fit_score_service import requirement_match_ratio, skill_sets_for_role_match


def resume_to_requirement_stats(
    resume_skills: list[str],
    required_skills: list[str],
) -> dict[str, Any]:
    """
    Compare resume skills to an explicit required-skill list.

    Builds a fresh cluster map from this pair (same normalization as job matching).
    """
    from app.services.skill_normalize import build_dynamic_cluster_map

    cmap = build_dynamic_cluster_map([*(resume_skills or []), *(required_skills or [])])
    _rk, req_keys, matched = skill_sets_for_role_match(
        resume_skills or [],
        required_skills or [],
        cmap,
    )
    n = len(req_keys)
    if n == 0:
        return {
            "requirement_match_ratio": None,
            "requirement_match_pct": None,
            "skills_matched_count": 0,
            "requirements_count": 0,
            "has_requirements": False,
            "match_basis": None,
        }

    ratio = requirement_match_ratio(matched, n)
    pct = max(0, min(100, round(100 * ratio)))
    return {
        "requirement_match_ratio": ratio,
        "requirement_match_pct": pct,
        "skills_matched_count": matched,
        "requirements_count": n,
        "has_requirements": True,
        "match_basis": "explicit_or_extracted_signals",
    }


def _resume_skills_in_listing_text(
    resume_skills: list[str],
    text_blob: str,
) -> dict[str, Any]:
    """
    Fallback when we have no job skill tokens: fraction of (non-trivial) resume
    skills whose normalized form appears in the job title + description text.
    """
    from app.services.skill_normalize import build_dynamic_cluster_map, normalize_skill_for_match

    rs = [s for s in (resume_skills or []) if s and str(s).strip()]
    if not rs:
        return {
            "requirement_match_ratio": None,
            "requirement_match_pct": None,
            "skills_matched_count": 0,
            "requirements_count": 0,
            "has_requirements": False,
            "match_basis": None,
        }

    cmap = build_dynamic_cluster_map(rs)
    raw = (text_blob or "").lower()
    compact = re.sub(r"[\s\-_/]+", "", raw)
    alnum = re.sub(r"[^a-z0-9+#]", "", raw)

    matched = 0
    checked = 0
    for s in rs:
        k = normalize_skill_for_match(s, cmap)
        if len(k) < 2:
            continue
        checked += 1
        if k in compact or k in alnum:
            matched += 1

    if checked == 0:
        return {
            "requirement_match_ratio": None,
            "requirement_match_pct": None,
            "skills_matched_count": 0,
            "requirements_count": 0,
            "has_requirements": False,
            "match_basis": None,
        }

    ratio = requirement_match_ratio(matched, checked)
    pct = max(0, min(100, round(100 * ratio)))
    return {
        "requirement_match_ratio": ratio,
        "requirement_match_pct": pct,
        "skills_matched_count": matched,
        "requirements_count": checked,
        "has_requirements": True,
        "match_basis": "resume_skills_in_listing_text",
    }


def resume_to_job_match_stats(resume_skills: list[str], job: dict[str, Any]) -> dict[str, Any]:
    """
    Full job object: uses ``required_skills`` if present, else rich extraction from
    description + title, else substring match of resume skills in listing text.
    """
    from app.ingestors.utils import extract_job_match_signals

    title = (job.get("title") or "").strip()
    desc = (
        job.get("description_snippet")
        or job.get("description")
        or job.get("job_description")
        or ""
    )
    desc = str(desc).strip()

    required = [x for x in (job.get("required_skills") or []) if x and str(x).strip()]
    if not required:
        required = extract_job_match_signals(desc, title)

    stats = resume_to_requirement_stats(resume_skills, required)
    if stats["has_requirements"]:
        return stats

    blob = f"{title} {desc}"
    fb = _resume_skills_in_listing_text(resume_skills, blob)
    return fb

