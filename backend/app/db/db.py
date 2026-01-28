import sqlite3
import json
from pathlib import Path
import os

DB_FILE = Path(__file__).parent / "resumes.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        raw_text TEXT NOT NULL,
        skills TEXT,
        education TEXT,
        work_experience TEXT
    )
    """)
    conn.commit()
    conn.close()

def save_resume(parsed_resume: dict):
    db_path = os.path.abspath(DB_FILE)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO resumes (raw_text, skills, education, work_experience)
        VALUES (?, ?, ?, ?)
    """, (
        parsed_resume.get("raw_text", ""),
        json.dumps(parsed_resume.get("skills", [])),
        json.dumps(parsed_resume.get("education", {})),
        json.dumps(parsed_resume.get("work_experience", []))
    ))

    conn.commit()
    conn.close()

def get_all_resumes():
    """
    Return all resumes as structured dictionaries.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, raw_text, skills, education, work_experience FROM resumes")
    rows = cursor.fetchall()
    conn.close()

    resumes = []
    for row in rows:
        resumes.append({
            "id": row[0],
            "raw_text": row[1],
            "skills": json.loads(row[2]) if row[2] else [],
            "education": json.loads(row[3]) if row[3] else {},
            "work_experience": json.loads(row[4]) if row[4] else []
        })
    return resumes

