"""
Career-level inference for job listings.

Candidate level comes from the LLM in ``parse-and-recommend`` (stored on ``ResumeDB``).
Job level is inferred here from the posting's title + description.

Levels (YoE ranges):
  apprenticeship   0       — no paid experience
  intern           0+      — currently a student with little/no experience
  entry            0–2     — recent grad / first role
  mid              2–4     — independent contributor
  senior           4+      — leads / mentors
"""

from __future__ import annotations

import re

LEVEL_ORDER: dict[str, int] = {
    "apprenticeship": 0,
    "intern": 1,
    "entry": 2,
    "mid": 3,
    "senior": 4,
}

_YOE_PATTERN = re.compile(
    r"""
    (?:minimum|at\s+least|minimum\s+of|at\s+least\s+of)?\s*  # optional qualifier
    (\d+(?:\.\d+)?)                                           # the number (captured)
    \s*\+?\s*                                                 # optional "+"
    (?:to\s*\d+\s*)?                                          # optional "to N" range
    (?:years?|yrs?|yoe)                                       # unit: years / yrs / yoe
    (?:\s*of)?                                                # optional "of"
    (?:\s*(?:experience|exp|work\s+experience))?              # optional "experience"
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Title keywords (most reliable — checked first).
_TITLE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("senior",        ["senior", "sr.", " sr ", "lead ", "staff ", "principal", "l5", "l6"]),
    ("mid",           ["mid-level", "mid level", " iii", " ii", "l3", "l4"]),
    ("entry",         ["entry level", "entry-level", "junior", "jr.", " jr ", "new grad",
                       "associate", "l1", "l2", "graduate"]),
    ("intern",        ["intern", "internship", "co-op", "coop", "co op"]),
    ("apprenticeship",["apprentice", "apprenticeship", "trainee"]),
]

# Description-only keywords (used as final fallback after YoE extraction fails).
_DESC_KEYWORDS: list[tuple[str, list[str]]] = [
    ("senior",        ["senior", "sr.", " sr ", "lead engineer", "staff engineer",
                       "principal engineer", "seasoned", "extensive experience",
                       "deep expertise", "expert-level", "subject matter expert"]),
    ("mid",           ["mid-level", "mid level", "intermediate", " iii", " ii"]),
    ("entry",         ["entry level", "entry-level", "junior", "new grad", "recent grad",
                       "early career", "no experience required", "0-2 years",
                       "associate", "graduate", "fresh grad"]),
    ("intern",        ["intern", "internship", "co-op", "coop"]),
    ("apprenticeship",["apprentice", "apprenticeship", "trainee"]),
]


def _yoe_to_level(yoe: float) -> str:
    if yoe < 2.0:
        return "entry"
    if yoe < 4.0:
        return "mid"
    return "senior"


def infer_job_level(description: str, title: str = "") -> tuple[str | None, float | None]:
    """
    Returns ``(level, min_required_yoe)``.
    ``level`` is None when we cannot confidently infer it (keep the job).
    """
    title_l = (title or "").lower()
    desc_l = (description or "").lower()
    combined = f"{title_l} {desc_l}"

    # Title keywords are the most reliable signal.
    for level, keywords in _TITLE_KEYWORDS:
        if any(kw in title_l for kw in keywords):
            return level, None

    # Minimum explicit YoE requirement from description.
    yoe_matches = _YOE_PATTERN.findall(desc_l)
    if yoe_matches:
        min_yoe = min(float(y) for y in yoe_matches)
        return _yoe_to_level(min_yoe), min_yoe

    # Description keyword fallback.
    for level, keywords in _DESC_KEYWORDS:
        if any(kw in desc_l for kw in keywords):
            return level, None

    return None, None


# Levels where filtering is currently active.
# Mid and senior tiers are not yet fully validated, so candidates at those
# levels bypass the filter and see all jobs until the upper tiers are ready.
_ACTIVE_FILTER_LEVELS: frozenset[str] = frozenset({"apprenticeship", "intern", "entry"})


def level_compatible(candidate_level: str | None, job_level: str | None) -> bool:
    """
    True when the job level is appropriate for the candidate.

    Filtering is currently scoped to entry-level candidates and below
    (apprenticeship, intern, entry).  Mid and senior candidates bypass the
    filter entirely until those tiers are fully validated.

    For active levels:
    - Job must be within 1 level of the candidate (either direction).
    - Unknown job level defaults to "mid" so entry-level candidates aren't
      inadvertently shown senior roles that omitted a level tag.
    """
    if not candidate_level or candidate_level not in _ACTIVE_FILTER_LEVELS:
        return True
    _DEFAULT_JOB_LEVEL = "mid"
    effective_job_level = job_level or _DEFAULT_JOB_LEVEL
    c = LEVEL_ORDER.get(candidate_level, 2)
    j = LEVEL_ORDER.get(effective_job_level, 2)
    return abs(j - c) <= 1
