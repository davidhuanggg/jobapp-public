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

use the POST `/parse-and-recommend` endpoint: upload a file (pdf, docx), then click Execute. The response includes `resume_id`, `recommendations`, `learning_paths`, and **`skill_demand_across_recommended_roles`**: **`skills_to_focus_on`** (gap skills ranked by how many recommended roles want them — what to learn next), **`your_skills_in_demand`** (resume overlap), and **`by_skill`** for the full breakdown. Skills are matched with **structural cleanup + dynamic fuzzy clustering** (`app/services/skill_normalize.py`): resume skills and all role extractions in that request are pooled; **similar keys merge** (via `rapidfuzz` if installed, else a **stdlib `difflib` fallback**) so variants like `Postgres` / `PostgreSQL` align without a big hand-maintained synonym table. Small phrase fixes (e.g. `node.js` → `node`) still run before clustering.

**Semantic / “same meaning” matching (optional):** string fuzzy matching is not true synonym detection. For **word vectors / embeddings**, install `pip install -r backend/requirements-embeddings.txt`, set **`SKILL_USE_EMBEDDINGS=1`**, and optionally `SKILL_EMBED_MODEL=all-MiniLM-L6-v2` and `SKILL_EMBED_COSINE=0.82`. The backend then runs a second merge pass (`app/services/skill_semantic.py`) on cluster representatives using **SentenceTransformers** (first run may download the model). For production you can swap the encoder for an **embeddings API** (OpenAI, Voyage, etc.) and keep the same merge logic.

To fetch learning resources in a dedicated API (separate from parse/recommend), use POST `/learning-resources` with the **same** `resume_id` returned by `/parse-and-recommend`:
- `{"resume_id": 1}` — auto-derive role titles and learning paths from that saved resume (no `focused_role_roadmap`)
- `{"resume_id": 1, "role_titles": ["Backend Engineer", "Data Scientist"]}` — limit resources to those roles (no roadmap)
- `{"resume_id": 1, "role_titles": ["Backend Engineer"]}` — **one** explicit title → same resources **plus** **`focused_role_roadmap`** (ordered gap steps; LLM order when `GROQ_API_KEY` is set, else heuristic)

**Job match vs resume:** POST `/jobs/match` with **`resume_id`** adds **`requirement_match_pct`** (0–100) to each job and **sorts** listings by that value **descending**. Scoring uses the same internal signals as before (required skills, description/title tokens, or resume-in-listing fallback). Without `resume_id` / skills, that field is not set and order is unchanged.

If `resume_id` is wrong or stale, the API returns **404** (no fallback to another resume). For production multi-user apps, add auth and store a `user_id` on each resume so IDs cannot be guessed across users.

Learning resources combine a small **static catalog** (Python, SQL, Docker, etc.) with **resume-aware personalization** when `GROQ_API_KEY` is set: one model call per target role adds a short “why this skill for you” note and tailored Google search links per gap skill (no invented URLs). Without Groq, you still get catalog + generic search fallbacks.

To fetch matching jobs for role titles without a resume, use POST `/jobs/match` with body `{"role_titles": ["Backend Engineer", "Data Scientist"]}`.

**Job board APIs (optional):**
- **Adzuna**: Free, one aggregator. Good default if you want zero cost.
- **JSearch** (RapidAPI): Aggregates LinkedIn, Indeed, Glassdoor, ZipRecruiter, etc.; best coverage. Free tier ~200 req/month.
- **Greenhouse / Lever**: Used for official company career pages only (per-company boards). No global search; we already integrate these in `company_jobs_client.py` (Greenboard = Greenhouse job board).

If both Adzuna and JSearch credentials are set, results from both are merged and deduped.

NOTE:
This project is still being worked on currently.
