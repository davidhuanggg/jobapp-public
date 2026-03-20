import json
import re
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def _parse_skills_json(content: str) -> list[str]:
    """Tolerate markdown or extra text around JSON."""
    if not content:
        return []
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group())
        skills = data.get("skills")
        if not isinstance(skills, list):
            return []
        return [str(s).strip() for s in skills if str(s).strip()]
    except json.JSONDecodeError:
        return []


def extract_job_skills(role_title: str) -> list[str]:
    prompt = f"""
List the core technical skills required for the job role below.
Return JSON only.

Role: {role_title}

Format:
{{ "skills": ["skill1", "skill2"] }}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You return JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=300,
    )

    return _parse_skills_json(response.choices[0].message.content or "")

