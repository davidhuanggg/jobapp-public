import json
import logging
import os
import re
from dotenv import load_dotenv
from groq import Groq
from app.services.experience_level_service import (
    extract_min_yoe,
    resolve_candidate_yoe,
    yoe_compatible,
)

_log = logging.getLogger(__name__)

# ============================
# ENV SETUP
# ============================
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not found. Add it to your .env file.")

# ============================
# GROQ CLIENT
# ============================
client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = "llama-3.1-8b-instant"


# ============================
# HELPERS
# ============================
def extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {"recommended_roles": []}


# Matches full clauses/sentences that mention a YoE requirement, e.g.
#   "3+ years of experience in data analysis"
#   "Bachelor's degree and 8-12 years experience"
#   "Minimum 5 years of work experience required."
_YOE_SENTENCE_RE = re.compile(
    r"[^.;:\n]*"                  # leading context within the same clause
    r"\d+(?:\.\d+)?"             # the number
    r"\s*(?:\+|[-–—]\s*\d+(?:\.\d+)?)?\s*"
    r"(?:years?|yrs?|yoe)"       # unit
    r"[^.;:\n]*"                  # trailing context within the same clause
    r"[.;:\n]?",                  # optional punctuation at the end
    re.IGNORECASE,
)


def _strip_yoe_mentions(text: str) -> str:
    """Remove sentences/clauses that reference a specific YoE requirement."""
    cleaned = _YOE_SENTENCE_RE.sub("", text)
    # Collapse leftover whitespace and stray punctuation.
    cleaned = re.sub(r"\n{2,}", "\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"(?:^[\s,;:]+)|(?:[\s,;:]+$)", "", cleaned, flags=re.MULTILINE)
    return cleaned.strip()



# ============================
# MAIN RECOMMENDER
# ============================
def get_recommendations(
    skills: list[str],
    education: list[dict],
    work_experience: list[dict],
    *,
    career_level: str | None = None,
    years_of_experience: float | None = None,
):
    """
    Generate job recommendations using ONLY structured resume data.
    """

    if not skills and not work_experience:
        return {"recommended_roles": []}

    # ---- Education (LIST SAFE) ----
    education_section = (
        "\n".join(
            f"- Degree: {e.get('degree', 'N/A')}, "
            f"Field: {e.get('field', 'N/A')}, "
            f"Institution: {e.get('institution', 'N/A')}"
            for e in education
        )
        if education else "- N/A"
    )

    # ---- Work Experience (LIST SAFE) ----
    work_experience_section = (
        "\n".join(
            f"- {w.get('title', 'N/A')} at {w.get('company', 'N/A')} "
            f"({w.get('duration', 'N/A')})"
            for w in work_experience
        )
        if work_experience else "- N/A"
    )

    # ---- Seniority constraint (injected only when known) ----
    _LEVEL_MAX_YOE = {
        "apprenticeship": 0,
        "intern": 1,
        "entry": 2,
        "mid": 4,
        "senior": 99,
    }
    yoe_display = (
        f"{years_of_experience:.1f}" if years_of_experience is not None else "0"
    )
    if career_level in _LEVEL_MAX_YOE:
        max_yoe = _LEVEL_MAX_YOE[career_level]
        seniority_rule = (
            f"- The candidate has {yoe_display} years of paid experience "
            f"(career level: {career_level}). "
            f"ONLY recommend roles that require AT MOST {max_yoe} years of experience. "
            f"DO NOT recommend mid-level, senior, lead, staff, or principal roles."
        )
    else:
        seniority_rule = ""

    prompt = f"""
You are a job recommendation engine.

STRICT RULES:
- Use ONLY the information provided below.
- DO NOT infer, assume, or guess missing skills.
- Every recommended role MUST be directly supported by the skills or experience.
{seniority_rule}
- Return UP TO 10 roles. Fewer is fine if that is all that is genuinely justified.
- If no roles are justified, return an empty list.

Candidate Skills:
{chr(10).join(f"- {s}" for s in skills) if skills else "- N/A"}

Education:
{education_section}

Work Experience:
{work_experience_section}

Return JSON ONLY in this format — keep each "reason" to one concise sentence:
{{
  "recommended_roles": [
    {{
      "title": "Job title",
      "reason": "One sentence referencing specific skills or experience"
    }}
  ]
}}
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a precise JSON-only API."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=800,
    )

    raw_roles = extract_json(response.choices[0].message.content).get("recommended_roles", [])

    # Deterministic guard — drop roles whose title implies a seniority level
    # the candidate hasn't reached yet, regardless of what the LLM returned.
    # Uses the same resolve_candidate_yoe + yoe_compatible logic as job listing
    # filtering so the two layers are always in sync.
    #
    # Critically: resolve_candidate_yoe falls back to career_level when
    # years_of_experience is None, so a 0-year entry-level candidate whose
    # LLM-parsed YoE came back null is still correctly assigned a 0.0 floor.
    effective_yoe = resolve_candidate_yoe(years_of_experience, career_level)
    before = len(raw_roles)
    raw_roles = [
        r for r in raw_roles
        if yoe_compatible(effective_yoe, "", r.get("title", ""))
    ]
    dropped = before - len(raw_roles)
    if dropped:
        _log.info(
            "Filtered %d over-seniority role(s) for candidate "
            "(effective_yoe=%s  yoe=%s  level=%s)",
            dropped, effective_yoe, years_of_experience, career_level,
        )

    # Strip any YoE mentions the LLM snuck into the reason text.
    for r in raw_roles:
        if r.get("reason"):
            r["reason"] = _strip_yoe_mentions(r["reason"])

    return {"recommended_roles": raw_roles}


# ============================
# CAREER LEVEL EXTRACTION
# ============================
def extract_career_level(
    raw_text: str,
    work_experience: list[dict],
    education: list[dict],
) -> dict:
    """
    Use the LLM to infer years of experience, career level, and student status
    directly from the resume.

    Returns:
        {
          "years_of_experience": float | None,
          "career_level": "apprenticeship" | "intern" | "entry" | "mid" | "senior",
          "is_student": bool
        }

    Falls back to a safe default (entry, not student) when the LLM is
    unavailable or returns unparsable output.
    """
    _default = {"years_of_experience": None, "career_level": "entry", "is_student": False}

    if not GROQ_API_KEY or not raw_text:
        return _default

    work_section = (
        "\n".join(
            f"- {w.get('title', 'N/A')} at {w.get('company', 'N/A')} ({w.get('duration', 'N/A')})"
            for w in (work_experience or [])
        ) or "- N/A"
    )
    edu_section = (
        "\n".join(
            f"- {e.get('degree', 'N/A')}, {e.get('field', 'N/A')}, {e.get('institution', 'N/A')}"
            for e in (education or [])
        ) or "- N/A"
    )

    prompt = f"""You are analysing a resume to determine career level.

Work experience:
{work_section}

Education:
{edu_section}

Resume text (first 1500 chars):
{raw_text[:1500]}

Tasks:
1. Sum up all paid work experience durations. Give total as a decimal (e.g. 1.5 for 18 months). Return null if none.
2. Is the person CURRENTLY enrolled as a student (pursuing an active degree)? Answer true/false.
3. Assign ONE career level using ONLY these values and thresholds:
   - "apprenticeship": 0 YoE, no degree, no internships
   - "intern": currently a student with little/no paid experience
   - "entry": 0–2 years of paid experience (including recent grads)
   - "mid": 2–4 years of paid experience
   - "senior": 4+ years of paid experience

Return JSON ONLY:
{{
  "years_of_experience": <number or null>,
  "career_level": "<one of the 5 values above>",
  "is_student": <true or false>
}}"""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a precise JSON-only API. Return only valid JSON, no extra text."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=120,
        )
        raw = response.choices[0].message.content or ""
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return _default
        parsed = json.loads(match.group())
        yoe = parsed.get("years_of_experience")
        level = parsed.get("career_level", "entry")
        is_student = bool(parsed.get("is_student", False))
        valid_levels = {"apprenticeship", "intern", "entry", "mid", "senior"}
        if level not in valid_levels:
            level = "entry"
        return {
            "years_of_experience": float(yoe) if yoe is not None else None,
            "career_level": level,
            "is_student": is_student,
        }
    except Exception:
        return _default


# ============================
# ROLE EXPLANATION
# ============================
def explain_role(role_title: str, *, years_of_experience: float | None = None) -> str:
    yoe_ctx = ""
    if years_of_experience is not None:
        yoe_ctx = (
            f"\nThe candidate has {years_of_experience:.1f} years of experience. "
            f"Tailor your explanation to someone at that experience level. "
            f"DO NOT mention experience requirements that exceed {years_of_experience:.1f} years."
        )

    prompt = f"""
Explain the role "{role_title}" in detail:
- Typical responsibilities
- Required skills (technical and soft)
- Common industries
{yoe_ctx}
Do NOT include specific years-of-experience requirements or degree requirements.
Focus on what the role does and what skills are used.
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a career advisor AI."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=400,
    )

    text = response.choices[0].message.content.strip()
    return _strip_yoe_mentions(text)

