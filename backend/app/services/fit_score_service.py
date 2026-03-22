"""
Role / job fit as an **additive score** (`fit_score`).

Each **factor** contributes a value in **[0, 1]** (clamped). **`fit_score`** is the
**sum** of those factors, so it can exceed **1.0** as you add dimensions (skills,
experience alignment, education alignment, job title match, etc.). Higher is
better for ranking the best-matching role or listing.

- **`fit_score_normalized`**: `fit_score / factor_count` in ~[0, 1] (average strength).
- **`fit_score_pct`**: `round(100 * fit_score_normalized)` for simple 0–100 UI badges.
  Sorting should use **`fit_score`**, not `fit_score_pct`, so stronger multi-signal
  matches rank above weaker ones.

**Requirement match** (resume vs role/job required skills): treated as “fraction of
requirements satisfied”, **clamped to 1.0** (100%). Extra resume skills do not push
this above 100%.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.skill_normalize import normalize_skill_for_match

# Generic job-title tokens — de-emphasized when comparing titles (not skills).
_TITLE_STOPWORDS: frozenset[str] = frozenset(
    {
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
        "intern",
        "remote",
        "hybrid",
        "full",
        "time",
        "part",
        "the",
        "and",
        "for",
        "with",
    }
)


def _clamp_unit(x: float) -> float:
    """Clamp to [0, 1]; NaN becomes 0."""
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return 0.0
    if xf != xf:  # NaN
        return 0.0
    return max(0.0, min(1.0, xf))


def _pct_from_ratio(ratio: float) -> int:
    """Percentage from a 0–1 ratio; result always in 0–100."""
    return max(0, min(100, round(100 * _clamp_unit(ratio))))


def requirement_match_ratio(matched: int, required_count: int) -> float:
    """
    Fraction of required skills satisfied (0–1), **capped at 1.0**.

    Uses matched / required_count when ``required_count > 0``; otherwise returns 0.0.
    """
    if required_count <= 0:
        return 0.0
    return _clamp_unit(matched / required_count)


def _education_entries(education: Any) -> list[dict]:
    if education is None:
        return []
    if isinstance(education, list):
        return [e for e in education if isinstance(e, dict)]
    if isinstance(education, dict):
        return [education]
    return []


def education_text_blob(education: Any) -> str:
    parts: list[str] = []
    for e in _education_entries(education):
        parts.append(str(e.get("degree", "") or ""))
        parts.append(str(e.get("field", "") or ""))
        parts.append(str(e.get("university", "") or e.get("institution", "") or ""))
    return " ".join(parts).lower()


def _domain_tokens(title: str) -> set[str]:
    s = re.sub(r"[^\w\s]", " ", (title or "").lower())
    words = [w for w in s.split() if w and len(w) > 2 and w not in _TITLE_STOPWORDS]
    if not words:
        words = [w for w in (title or "").lower().split() if len(w) > 2]
    return set(words)


def jaccard_domain_tokens(a: str, b: str) -> float:
    """0–1 similarity of two titles using domain-ish tokens."""
    A, B = _domain_tokens(a), _domain_tokens(b)
    if not A and not B:
        return 1.0
    if not A or not B:
        return 0.0
    inter = len(A & B)
    union = len(A | B)
    raw = inter / union if union else 0.0
    return _clamp_unit(raw)


def _role_title_token_coverage_in_text(role_title: str, text_blob_lower: str) -> float:
    """
    Share of role title domain tokens that appear in text (0–1).
    If the role parses to no tokens, returns 0.5 (neutral).
    """
    rt = _domain_tokens(role_title)
    if not rt:
        return 0.5
    if not (text_blob_lower or "").strip():
        return 0.0
    et = set(re.findall(r"[a-z0-9]+", text_blob_lower))
    et = {t for t in et if len(t) > 2 and t not in _TITLE_STOPWORDS}
    if not et:
        return 0.0
    matched = len(rt & et)
    return _clamp_unit(matched / len(rt))


def experience_text_blob(work_experience: list[dict] | None) -> str:
    parts: list[str] = []
    for w in work_experience or []:
        if not isinstance(w, dict):
            continue
        parts.append(str(w.get("title") or w.get("position") or ""))
        parts.append(str(w.get("company") or ""))
    return " ".join(parts).lower()


def role_title_vs_experience_ratio(role_title: str, work_experience: list[dict] | None) -> float:
    return _role_title_token_coverage_in_text(role_title, experience_text_blob(work_experience))


def role_title_vs_education_ratio(role_title: str, education: Any) -> float:
    return _role_title_token_coverage_in_text(role_title, education_text_blob(education))


def skill_sets_for_role_match(
    resume_skills: list[str],
    role_skills: list[str],
    cluster_map: dict[str, str],
) -> tuple[set[str], set[str], int]:
    resume_keys = {
        normalize_skill_for_match(s, cluster_map)
        for s in (resume_skills or [])
        if normalize_skill_for_match(s, cluster_map)
    }
    role_keys = {
        normalize_skill_for_match(s, cluster_map)
        for s in (role_skills or [])
        if normalize_skill_for_match(s, cluster_map)
    }
    matched = len(resume_keys & role_keys)
    return resume_keys, role_keys, matched


def _additive_fit_payload(
    *,
    factor_ratios: list[tuple[str, float]],
) -> dict[str, Any]:
    """
    factor_ratios: (name, value in [0,1]) — only include factors that apply.
    fit_score = sum(values); can exceed 1 when len > 1.
    """
    terms: list[tuple[str, float]] = [(n, _clamp_unit(v)) for n, v in factor_ratios]
    fit_score = round(sum(v for _n, v in terms), 4)
    n = len(terms)
    normalized = fit_score / n if n else 0.0
    pct = max(0, min(100, round(100 * normalized)))
    return {
        "fit_score": fit_score,
        "fit_factor_count": n,
        "fit_score_normalized": round(normalized, 4),
        "fit_score_pct": pct,
        "fit_breakdown": {
            "factors_summed": [n for n, _ in terms],
            "factor_values": {n: v for n, v in terms},
        },
    }


def compute_role_fit_percent(
    *,
    resume_skills: list[str],
    work_experience: list[dict] | None,
    education: Any = None,
    role_title: str,
    role_skills: list[str],
    cluster_map: dict[str, str],
) -> dict[str, Any]:
    """
    Additive fit: skills + experience/title + education/title (each 0–1), summed.
    """
    _resume_keys, role_keys, matched = skill_sets_for_role_match(
        resume_skills, role_skills, cluster_map
    )
    required_n = len(role_keys)
    exp_ratio = role_title_vs_experience_ratio(role_title, work_experience)
    edu_ratio = role_title_vs_education_ratio(role_title, education)

    factor_ratios: list[tuple[str, float]] = [
        ("experience_title", exp_ratio),
        ("education_title", edu_ratio),
    ]
    if required_n > 0:
        skill_ratio = requirement_match_ratio(matched, required_n)
        factor_ratios.insert(0, ("skills_vs_role", skill_ratio))
    else:
        skill_ratio = None

    base = _additive_fit_payload(factor_ratios=factor_ratios)
    bd = base["fit_breakdown"]
    bd["requirement_match_ratio"] = skill_ratio
    bd["skill_match_pct"] = None if skill_ratio is None else _pct_from_ratio(skill_ratio)
    bd["experience_title_match_pct"] = _pct_from_ratio(exp_ratio)
    bd["education_title_match_pct"] = _pct_from_ratio(edu_ratio)
    bd["skills_matched_count"] = matched
    bd["role_skills_considered"] = required_n
    return base


def compute_job_fit_percent(
    *,
    candidate_skills: list[str],
    required_skills: list[str],
    role_query_title: str,
    job_title: str,
) -> dict[str, Any]:
    """
    Additive fit: job skills coverage + listing title vs query role (each 0–1), summed.
    """
    from app.services.skill_normalize import build_dynamic_cluster_map

    cmap = build_dynamic_cluster_map([*candidate_skills, *required_skills])
    cand_set = {
        normalize_skill_for_match(s, cmap)
        for s in (candidate_skills or [])
        if normalize_skill_for_match(s, cmap)
    }
    req_set = {
        normalize_skill_for_match(s, cmap)
        for s in (required_skills or [])
        if normalize_skill_for_match(s, cmap)
    }
    title_fit = jaccard_domain_tokens(role_query_title, job_title)

    req_n = len(req_set)
    if req_set:
        hits = len(cand_set & req_set)
        skill_fit = requirement_match_ratio(hits, req_n)
        factor_ratios = [
            ("skills_vs_job", skill_fit),
            ("title_match", title_fit),
        ]
    else:
        skill_fit = None
        factor_ratios = [("title_match", title_fit)]

    base = _additive_fit_payload(factor_ratios=factor_ratios)
    bd = base["fit_breakdown"]
    bd["requirement_match_ratio"] = skill_fit
    bd["skill_match_pct"] = None if skill_fit is None else _pct_from_ratio(skill_fit)
    bd["title_match_pct"] = _pct_from_ratio(title_fit)
    bd["skills_matched_count"] = len(cand_set & req_set) if req_set else 0
    bd["job_skills_considered"] = len(req_set)
    return base
