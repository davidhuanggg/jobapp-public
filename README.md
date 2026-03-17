JobApp — Resume Parser & Career Exploration Tool
Most job search tools match your resume to jobs you already know about. JobApp does the opposite — it reads your resume, understands your actual skills and experience, and surfaces roles in industries you might not have considered or didn't think were accessible to you.
Upload a resume. Get back a set of job recommendations with context for why your background fits — even when it's not obvious.
Live demo: https://jobapp-public.onrender.com/docs

**What it does**

Parses uploaded resumes (PDF or DOCX)
Extracts structured data: skills, experience, education
Uses an LLM (Groq) to reason about transferable skills across industries
Returns job role recommendations with explanations

**Tech Stack**

Python 3.12 / FastAPI
Pydantic for data validation
Groq LLM API for recommendations
SQLAlchemy
Pytest for testing
Uvicorn

Run locally
bashgit clone https://github.com/davidhuanggg/jobapp-public.git
cd jobapp-public/backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file inside `backend/services/`:
```
GROQ_API_KEY=your_key_here
Get a free key at console.groq.com
bashuvicorn app.main:app --reload
API available at http://127.0.0.1:8000 — Swagger UI at /docs
Use POST /parse_and_recommend to upload a resume and get recommendations.
