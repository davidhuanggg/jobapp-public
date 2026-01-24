import json
import requests
from pathlib import Path
import os


from dotenv import load_dotenv
import os

load_dotenv()  # ← THIS reads the .env file

print(os.getenv("GROQ_API_KEY"))  # test

# ============================
# CONFIG
# ============================
FASTAPI_URL = "http://127.0.0.1:8000/parse-resume"
RESUME_PATH = Path("resume.pdf")
OUTPUT_PATH = Path("job_recommendations.json")

# ============================
# GROQ CLIENT (REAL VERSION)
# ============================
from groq import Groq

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")  # export GROQ_API_KEY=...
)

def groq_call(prompt: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a career advisor AI. "
                    "You MUST return ONLY valid JSON. "
                    "Do NOT include explanations, markdown, or extra text."
                )
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    return response.choices[0].message.content

def explain_role(role_title: str) -> str:
    """
    Call Groq to explain a job role in depth.
    Returns a string with duties, responsibilities, and key skills.
    """
    prompt = f"""
You are a career advisor AI.

Please explain the following job role in detail:
- Typical duties
- Key responsibilities
- Skills usually required

Return the explanation in plain text. Role: "{role_title}"
"""
    return groq_call(prompt)

# ============================
# 1️⃣ CALL RESUME PARSER
# ============================
if not RESUME_PATH.exists():
    raise FileNotFoundError(f"Resume not found: {RESUME_PATH}")

with RESUME_PATH.open("rb") as f:
    response = requests.post(
        FASTAPI_URL,
        files={"file": f},
        timeout=30
    )

if response.status_code != 200:
    raise RuntimeError(f"Parser error: {response.status_code}\n{response.text}")

resume = response.json()

# ============================
# 2️⃣ EXTRACT CONTEXT SAFELY
# ============================
name = resume.get("name", "Unknown")
skills = resume.get("skills", [])
education = resume.get("education", [])
experience = resume.get("experience", [])
raw_text = resume.get("raw_text", "")

# ============================
# 3️⃣ BUILD HIGH-QUALITY PROMPT
# ============================
prompt = f"""
Candidate Name: {name}

SKILLS:
{json.dumps(skills, indent=2)}

EXPERIENCE:
{json.dumps(experience, indent=2)}

EDUCATION:
{json.dumps(education, indent=2)}

FULL RESUME TEXT:
{raw_text}

TASK:
Based on this candidate’s background, recommend the BEST job roles.

Return JSON ONLY in the following format:

{{
  "recommended_roles": [
    {{
      "title": "Job Title",
      "reason": "Why this role fits the candidate"
    }}
  ]
}}
"""

# ============================
# 4️⃣ SEND TO GROQ
# ============================
llm_response = groq_call(prompt)

try:
    recommendations = json.loads(llm_response)
    for role in recommendations.get("recommended_roles", []):
    	explanation = explain_role(role["title"])
    	role["detailed_explanation"] = explanation
except json.JSONDecodeError:
    recommendations = {
        "error": "LLM did not return valid JSON",
        "raw_output": llm_response
    }

# ============================
# 5️⃣ SAVE OUTPUT
# ============================
with OUTPUT_PATH.open("w") as f:
    json.dump(recommendations, f, indent=2)

print(f"Enhanced job recommendations saved to {OUTPUT_PATH.resolve()}")

print("\n✅ Job recommendations generated")
print(json.dumps(recommendations, indent=2))
print(f"\n📁 Saved to: {OUTPUT_PATH.resolve()}")

