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

create a .env file (touch .env) inside the services directory and get a free api key from groq https://console.groq.com/home

edit the .env file with (nano .env) and add GROQ_API_KEY = YOUR UNIQUE API KEY FROM GROQ

run the app uvicorn app.main:app --reload at backend directory

the API will be available at:
http://127.0.0.1:8000
swagger UI: http://127.0.0.1:8000/docs

use the POST /parse_and_recommend
upload a file(pdf,docx)

click execute

NOTE:
This project is still being worked on currently.
