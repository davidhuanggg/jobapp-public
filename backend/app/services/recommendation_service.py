import json
import os
import re
from dotenv import load_dotenv
from groq import Groq

# ============================
# ENV SETUP
# ============================
load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    raise RuntimeError("GROQ_API_KEY not found. Add it to your .env file.")

# ============================
# GROQ CLIENT
# ============================
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = "llama-3.1-8b-instant"

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise RuntimeError("GROQ_API_KEY not found. Add it to your .env file.")

client = Groq(api_key=api_key)

def extract_json(text: str) -> dict:
    import re, json
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {}

def get_recommendations(
    skills: list[str],
    education: dict,
    work_experience: list[dict],
):
    """
    Generate job recommendations using ONLY structured resume data.
    """

    if not skills and not work_experience:
        raise ValueError("Insufficient resume data to generate recommendations")

    prompt = f"""
You are a job recommendation engine.

STRICT RULES:
- Use ONLY the information provided below.
- DO NOT infer, assume, or guess missing skills.
- Every recommended role MUST be directly supported by the skills or experience.
- If fewer than 10 roles are justified, return fewer.
- If no roles are justified, return an empty list.

Candidate Skills:
{chr(10).join(f"- {s}" for s in skills)}

Education:
- Degree: {education.get("degree", "N/A")}
- Field: {education.get("field", "N/A")}
- Institution: {education.get("institution", "N/A")}

Work Experience:
{chr(10).join(
    f"- {w.get('title')} at {w.get('company')} ({w.get('duration', 'N/A')})"
    for w in work_experience
)}

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
	model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a precise JSON-only API."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
        max_tokens=700,
    )

    return json.loads(response.choices[0].message.content)

def explain_role(role_title: str) -> str:
    prompt = f"Explain the role '{role_title}' in detail (duties, skills, industries)."
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a career advisor AI."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content
