import json
import requests
from pathlib import Path
import os
from dotenv import load_dotenv
from groq import Groq

# ============================
# ENV SETUP
# ============================
load_dotenv()  # load .env variables

if not os.getenv("GROQ_API_KEY"):
    raise RuntimeError("GROQ_API_KEY not found. Add it to your .env file.")

# ============================
# CONFIG
# ============================
FASTAPI_URL = "http://127.0.0.1:8000/parse-resume"
RESUME_PATH = Path("resume.pdf")
OUTPUT_PATH = Path("job_recommendations.json")
GROQ_MODEL = "llama-3.1-8b-instant"  # currently supported Groq model

# ============================
# GROQ CLIENT
# ============================
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ============================
# HELPER FUNCTIONS
# ============================
def groq_call(prompt: str) -> str:
    """
    Send a prompt to Groq and return the response text.
    """
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a career advisor AI. "
                    "You MUST return ONLY valid JSON when asked. "
                    "Do NOT include explanations, markdown, or extra text unless requested."
                )
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content

def extract_json(text: str) -> dict:
    """
    Fallback parser: extracts JSON object from text in case LLM adds extra text.
    """
    import re
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM output")
    return json.loads(match.group())

def explain_role(role_title: str) -> str:
    """
    Generate an in-depth explanation of a job role.
    """
    prompt = f"""
You are a career advisor AI.

Please explain the following job role in detail:
- Typical duties
- Key responsibilities
- Skills usually required
- Also suggest industries the candidate might enjoy exploring beyond their previous experience.

Return the explanation in plain text. Role: "{role_title}"
"""
    return groq_call(prompt)

# ============================
# 1️⃣ PARSE RESUME
# ============================
if not RESUME_PATH.exists():
    raise FileNotFoundError(f"Resume not found: {RESUME_PATH}")

with RESUME_PATH.open("rb") as f:
    response = requests.post(FASTAPI_URL, files={"file": f}, timeout=30)

if response.status_code != 200:
    raise RuntimeError(f"Parser error: {response.status_code} - {response.text}")

resume_data = response.json()
raw_text = resume_data.get("raw_text", "")

# ============================
# 5️⃣ UPSKILL / LEARNING PATH
# ============================
def recommend_learning_path(candidate_skills: list[str], role_title: str, role_skills: list[str]) -> dict:
    """
    Generate a learning path for missing skills using Groq.
    """
    # Compute missing skills
    missing_skills = list(set(role_skills) - set(candidate_skills))
    if not missing_skills:
        return {
            "role": role_title,
            "missing_skills": [],
            "learning_path": []
        }

    # Build prompt for Groq
    prompt = f"""
The user wants to become a {role_title}. 
They currently know: {', '.join(candidate_skills)}.
They are missing these skills: {', '.join(missing_skills)}.

Please recommend for each missing skill:
- Online courses or tutorials
- Suggested projects to practice the skill
- Estimated time to become proficient

Return JSON ONLY in this format:

{{
  "role": "{role_title}",
  "missing_skills": {missing_skills},
  "learning_path": [
    {{
      "skill": "Skill Name",
      "courses": ["Course Name or URL", ...],
      "projects": ["Project ideas ..."],
      "estimated_time": "X weeks"
    }}
  ]
}}
"""

    # Call Groq
    llm_output = groq_call(prompt)
    try:
        return extract_json(llm_output)
    except Exception as e:
        # fallback in case LLM returns extra text
        return {
            "role": role_title,
            "missing_skills": missing_skills,
            "learning_path": [],
            "error": f"LLM output could not be parsed: {e}",
            "raw_output": llm_output
        }


# ============================
# 2️⃣ GENERATE RECOMMENDED JOB ROLES
# ============================
prompt_roles = f"""
Candidate Resume:

{raw_text}

TASK:
Recommend job roles for this candidate.

Include:
- Common roles that match the candidate’s skills
- Less common or non-traditional roles that could interest the candidate, even if they require slightly different skills
- Explain why each role is a good fit or interesting

Return JSON ONLY in this format:

{{
  "recommended_roles": [
    {{
      "title": "Job Title",
      "reason": "Why this role fits the candidate or could be interesting"
    }}
  ]
}}
"""
try:
    llm_output = groq_call(prompt_roles)
    recommendations = extract_json(llm_output)
except Exception as e:
    raise RuntimeError(f"Error parsing LLM output: {e}\nRaw output:\n{llm_output}")

# ============================
# 3️⃣ ADD DETAILED ROLE EXPLANATIONS
# ============================
for role in recommendations.get("recommended_roles", []):
    try:
        explanation = explain_role(role["title"])
        role["detailed_explanation"] = explanation
    except Exception as e:
        role["detailed_explanation"] = f"Error generating explanation: {e}"

# Suppose we have candidate_skills extracted from resume
# Example (you may replace with your actual parsing logic)
candidate_skills = ["Python", "SQL", "Pandas", "Machine Learning basics"]

# Suppose we have a typical skill map for roles (simplified example)
role_skill_map = {
    "Machine Learning Engineer": ["Python", "NumPy", "TensorFlow", "PyTorch", "SQL", "ML pipelines"],
    "Data Scientist": ["Python", "Pandas", "NumPy", "SQL", "Statistics", "ML models"]
}

# Ask user which role they want to upskill for
chosen_role = "Machine Learning Engineer"

learning_path = recommend_learning_path(
    candidate_skills=candidate_skills,
    role_title=chosen_role,
    role_skills=role_skill_map.get(chosen_role, [])
)

# Add to recommendations JSON
for role in recommendations.get("recommended_roles", []):
    if role["title"] == chosen_role:
        role["learning_path"] = learning_path.get("learning_path", [])
        role["missing_skills"] = learning_path.get("missing_skills", [])


# ============================
# 4️⃣ SAVE FINAL OUTPUT
# ============================
with OUTPUT_PATH.open("w") as f:
    json.dump(recommendations, f, indent=2)

print("\nJob recommendations with explanations generated!")
print(json.dumps(recommendations, indent=2))
print(f"\n📁 Saved to: {OUTPUT_PATH.resolve()}")

