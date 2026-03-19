JobApp - Resume Parsing & Job Recommendation API

A FastAPI backend that:
- Parses uploaded resumes
- Extracts structured resume information
- Generates job role recommendations using an LLM(Groq)

This project is intended as a backend service for a future job-search or career guidance app

Features:

- Resume upload & parsing
- Strucutured resume extraction (skills,education,experience)
- AI-powered job recommendations
- **Matching real jobs**: finds jobs that match recommendations via job board APIs and official company career pages (see below)
- FastAPI + pydantic models
- Environment-based API key management

Tech Stack:

- Python 3.12+
- FastAPI
- Pydantic
- Groq LLM API
- Pytest(testing)
- Uvicorn

Steps to install:
Clone the repo:
git clone https://github.com/davidhuanggg/jobapp-public.git
Access backend directory

create virtual environment

pip install -r requirements.txt

create a .env file (touch .env) inside the services directory and get a free api key from groq https://console.groq.com/home

edit the .env file with (nano .env) and add:

- `GROQ_API_KEY = YOUR UNIQUE API KEY FROM GROQ` (required)
- Optional, for job matching:
  - **Adzuna** (free): `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` from [Adzuna Developer](https://developer.adzuna.com/). `ADZUNA_COUNTRY=us` (or `gb`, etc.) if needed.
  - **JSearch** (RapidAPI, best coverage — LinkedIn/Indeed/Glassdoor/etc.): `RAPIDAPI_KEY` from [RapidAPI JSearch](https://www.rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch). Free tier ~200 req/month.
  - **Official company career pages** (Greenhouse/Lever): no extra keys; we fetch from a built-in list of companies (see `company_jobs_client.py`). “Greenboard” = Greenhouse job board = already used here per-company.

run the app uvicorn app.main:app --reload at backend directory

the API will be available at:
http://127.0.0.1:8000
swagger UI: http://127.0.0.1:8000/docs

use the POST `/parse-and-recommend` endpoint: upload a file (pdf, docx), then click Execute. The response includes `recommendations` with a `matching_jobs` array per role (from job boards and company career pages).

To only fetch matching jobs for role titles without a resume, use POST `/jobs/match` with body `{"role_titles": ["Backend Engineer", "Data Scientist"]}`.

**Job board APIs (optional):**
- **Adzuna**: Free, one aggregator. Good default if you want zero cost.
- **JSearch** (RapidAPI): Aggregates LinkedIn, Indeed, Glassdoor, ZipRecruiter, etc.; best coverage. Free tier ~200 req/month.
- **Greenhouse / Lever**: Used for official company career pages only (per-company boards). No global search; we already integrate these in `company_jobs_client.py` (Greenboard = Greenhouse job board).

If both Adzuna and JSearch credentials are set, results from both are merged and deduped.

NOTE:
This project is still being worked on currently.
