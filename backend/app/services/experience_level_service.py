"""
YoE-based filtering for job listings.

Filtering is a two-layer process:

  Layer 1 — explicit:  find the lowest numeric YoE requirement written in the
                       job title, description, or qualifications bullets.
  Layer 2 — implicit:  when no number is present, infer a floor from seniority
                       keywords in the job title ("Senior" → 4 yrs, etc.).

If neither layer produces a requirement, the job is kept (we can't prove it's
wrong for the candidate).  This is intentional: an unlabelled "Software
Engineer" posting is not necessarily wrong for a 1-year candidate.

Public API
----------
resolve_candidate_yoe   -- turn all candidate data into one concrete YoE floor
extract_min_yoe         -- pull the lowest explicit YoE from any text block
infer_title_min_yoe     -- infer implicit YoE floor from title keywords alone
yoe_compatible          -- final yes/no gate combining both layers
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Candidate-side: resolve a concrete YoE from whatever data we have
# ---------------------------------------------------------------------------

# Safe YoE floor for each career level when explicit years aren't recorded.
# Entry/intern/apprenticeship → 0 (little or no paid experience, by definition).
# Mid → 2 (minimum of the 2–4 year band).
# Senior → 4 (minimum of the 4+ year band).
_LEVEL_YOE_FLOOR: dict[str, float] = {
    "apprenticeship": 0.0,
    "intern":         0.0,
    "entry":          0.0,
    "mid":            2.0,
    "senior":         4.0,
}


def resolve_candidate_yoe(
    years_of_experience: float | None,
    career_level: str | None,
) -> float | None:
    """
    Return a concrete years-of-experience floor for filtering.

    Priority:
    1. Use ``years_of_experience`` directly when the LLM measured it.
    2. Fall back to ``career_level`` as a proxy (entry/intern/apprenticeship
       → 0, mid → 2, senior → 4).
    3. Return ``None`` only when we have no information at all — the filter
       will then treat every job as compatible rather than guess.
    """
    if years_of_experience is not None:
        return years_of_experience
    return _LEVEL_YOE_FLOOR.get(career_level)  # None if level is unknown


# ---------------------------------------------------------------------------
# Job-side layer 1: extract the explicit numeric YoE from posting text
# ---------------------------------------------------------------------------

_YOE_PATTERN = re.compile(
    r"""
    (?:minimum|at\s+least|minimum\s+of|at\s+least\s+of)?\s*  # optional qualifier
    (\d+(?:\.\d+)?)                                           # the number (captured)
    \s*                                                       # optional whitespace
    (?:                                                       # optional range / plus
        \+                                                    #   "2+"
      | (?:[-–—]\s*\d+(?:\.\d+)?)                            #   "8-12" / "6–10"
      | (?:to\s*\d+(?:\.\d+)?)                               #   "3 to 5"
    )?\s*
    (?:years?|yrs?|yoe)                                       # unit: years / yrs / yoe
    (?:\s*of)?                                                # optional "of"
    (?:\s*(?:experience|exp|work\s+experience))?              # optional "experience"
    """,
    re.IGNORECASE | re.VERBOSE,
)


def extract_min_yoe(text: str | None) -> float | None:
    """
    Pull the minimum years-of-experience number from any text block.

    Returns the smallest YoE figure found (the true floor when a posting
    lists multiple tiers such as "3 yrs with a Masters OR 5 yrs with a
    Bachelor's"), or ``None`` if the description doesn't mention a specific
    requirement.
    """
    matches = _YOE_PATTERN.findall((text or "").lower())
    if not matches:
        return None
    return min(float(y) for y in matches)


# ---------------------------------------------------------------------------
# Job-side layer 2: infer implicit YoE floor from title seniority keywords
# ---------------------------------------------------------------------------

# Titles that imply little or no prior experience required.
_ENTRY_TITLE_RE = re.compile(
    r"\b(junior|jr\.?|entry[\s-]?level|entry|graduate|grad|intern|internship"
    r"|trainee|apprentice|associate)\b",
    re.IGNORECASE,
)

# Titles that imply ~2+ years of relevant experience.
_MID_TITLE_RE = re.compile(
    r"\b(mid[\s-]?level|mid|intermediate)\b",
    re.IGNORECASE,
)

# Titles that imply 4+ years of experience.  Word boundaries prevent matching
# "assisting" or "leadership" as false positives.
_SENIOR_TITLE_RE = re.compile(
    r"\b(senior|sr\.?|lead|staff|principal|manager|director|head\s+of"
    r"|vp|vice[\s-]?president|chief|architect)\b",
    re.IGNORECASE,
)

# Approximate YoE floors assigned to each seniority tier.
_ENTRY_YOE  = 0.0
_MID_YOE    = 2.0
_SENIOR_YOE = 4.0


def infer_title_min_yoe(title: str) -> float | None:
    """
    Return a YoE floor inferred from seniority keywords in a job title.

    Returns ``None`` when the title has no clear seniority marker (e.g.
    "Software Engineer", "Data Analyst") — the caller should treat that
    as "no opinion" rather than a hard block.

    Examples
    --------
    >>> infer_title_min_yoe("Senior Data Analyst")
    4.0
    >>> infer_title_min_yoe("Junior Software Engineer")
    0.0
    >>> infer_title_min_yoe("Data Analyst")   # no keyword
    None
    """
    if not title:
        return None
    if _ENTRY_TITLE_RE.search(title):
        return _ENTRY_YOE
    if _MID_TITLE_RE.search(title):
        return _MID_YOE
    if _SENIOR_TITLE_RE.search(title):
        return _SENIOR_YOE
    return None


# ---------------------------------------------------------------------------
# Gate: does this job fit this candidate?
# ---------------------------------------------------------------------------

def yoe_compatible(
    candidate_yoe: float | None,
    description: str,
    title: str = "",
    qualifications: list[str] | None = None,
) -> bool:
    """
    ``True`` when the job posting is appropriate for the candidate's years of
    experience.

    Two-layer check
    ---------------
    Layer 1 — explicit requirement:
        Scans the combined text of title + description + qualifications bullets
        for any "N years of experience" phrasing.  When found, the minimum
        across all matches is the requirement.

    Layer 2 — title-implied requirement:
        When no explicit number is found, the seniority level implied by the
        job title is used as a proxy floor ("Senior" → 4 yrs, "Mid" → 2 yrs,
        "Junior/Entry/Intern" → 0 yrs).

    If neither layer finds a signal, the job is kept (no data → no block).
    If ``candidate_yoe`` is ``None``, the job is kept (caller has no data).
    """
    # No candidate data → cannot make a judgment, keep the job.
    if candidate_yoe is None:
        return True

    # Layer 1: look for an explicit YoE number anywhere in the posting text.
    parts = [title or "", description or ""]
    if qualifications:
        parts.extend(q for q in qualifications if isinstance(q, str))
    combined = " ".join(parts)

    required_yoe = extract_min_yoe(combined)
    if required_yoe is not None:
        return candidate_yoe >= required_yoe

    # Layer 2: no number found — fall back to title keywords.
    title_floor = infer_title_min_yoe(title or "")
    if title_floor is not None:
        return candidate_yoe >= title_floor

    # No signal at all → keep the job.
    return True
