import json
import os
import re
from dotenv import load_dotenv
from groq import Groq

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


# ============================
# MAIN RECOMMENDER
# ============================
def get_recommendations(
    skills: list[str],
    education: list[dict],
    work_experience: list[dict],
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

    prompt = f"""
You are a job recommendation engine.

STRICT RULES:
- Use ONLY the information provided below.
- DO NOT infer, assume, or guess missing skills.
- Every recommended role MUST be directly supported by the skills or experience.
- Return EXACTLY 10 roles — no more, no fewer (unless fewer than 10 are genuinely justified).
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
        temperature=0.6,
        max_tokens=800,
    )

    return extract_json(response.choices[0].message.content)


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
def explain_role(role_title: str) -> str:
    prompt = f"""
Explain the role "{role_title}" in detail:
- Typical responsibilities
- Required skills
- Common industries
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

    return response.choices[0].message.content.strip()

