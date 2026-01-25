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

create a .env file inside the services directory

run the app uvicorn app.main:app --reload at backend directory

the API will be available at:
http://127.0.0.1:8000
swagger UI: http://127.0.0.1:8000/docs

use the POST /parse-resume
upload a file(pdf,docx)

NOTE:
This project is still being worked on currently.
