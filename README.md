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

create a .env file (touch .env) inside the services directory and get a free api key from groq https://console.groq.com/home

edit the .env file with (nano .env) and add:

- `GROQ_API_KEY = YOUR UNIQUE API KEY FROM GROQ` (required)
- Optional, for job matching:
  - **Adzuna** (free): `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` from [Adzuna Developer](https://developer.adzuna.com/). `ADZUNA_COUNTRY=us` (or `gb`, etc.) if needed.
  - **JSearch** (RapidAPI, best coverage — LinkedIn/Indeed/Glassdoor/etc.): `RAPIDAPI_KEY` from [RapidAPI JSearch](https://www.rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch). Free tier ~200 req/month.
- **Official company career pages** (Greenhouse/Lever): no extra keys; we auto-discover which companies to fetch by parsing Greenhouse/Lever tokens from job URLs returned by job-board APIs (fallback to a small default list if discovery fails).

run the app uvicorn app.main:app --reload at backend directory

the API will be available at:
http://127.0.0.1:8000
swagger UI: http://127.0.0.1:8000/docs

use the POST `/parse-and-recommend` endpoint: upload a file (pdf, docx), then click Execute. The response includes `recommendations` and `learning_paths`.

To fetch matching jobs for role titles without a resume, use POST `/jobs/match` with body `{"role_titles": ["Backend Engineer", "Data Scientist"]}`.

**Job board APIs (optional):**
- **Adzuna**: Free, one aggregator. Good default if you want zero cost.
- **JSearch** (RapidAPI): Aggregates LinkedIn, Indeed, Glassdoor, ZipRecruiter, etc.; best coverage. Free tier ~200 req/month.
- **Greenhouse / Lever**: Used for official company career pages only (per-company boards). No global search; we already integrate these in `company_jobs_client.py` (Greenboard = Greenhouse job board).

If both Adzuna and JSearch credentials are set, results from both are merged and deduped.

NOTE:
This project is still being worked on currently.
