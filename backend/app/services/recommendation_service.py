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
- If fewer than 10 roles are justified, return fewer.
- If no roles are justified, return an empty list.

Candidate Skills:
{chr(10).join(f"- {s}" for s in skills) if skills else "- N/A"}

Education:
{education_section}

Work Experience:
{work_experience_section}

Return JSON ONLY in this format:
{{
  "recommended_roles": [
    {{
      "title": "Job title",
      "reason": "Explanation referencing specific skills or experience"
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
        max_tokens=700,
    )

    return extract_json(response.choices[0].message.content)


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

