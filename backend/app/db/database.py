# backend/app/db/database.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./resumes.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # required for SQLite + FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Columns added after initial schema — safe to run on every startup.
_MIGRATIONS: list[str] = [
    "ALTER TABLE resumes ADD COLUMN years_of_experience REAL",
    "ALTER TABLE resumes ADD COLUMN career_level VARCHAR",
    "ALTER TABLE resumes ADD COLUMN is_student BOOLEAN DEFAULT 0",
]


def _run_migrations(engine=None) -> None:
    """Apply additive column migrations that SQLAlchemy create_all won't handle.

    ``engine`` defaults to the module-level engine; pass a custom engine in
    tests to target an in-memory database.
    """
    _engine = engine or globals()["engine"]
    with _engine.connect() as conn:
        for stmt in _MIGRATIONS:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                # Column already exists — safe to ignore.
                pass


def init_db():
    from app.db import models
    Base.metadata.create_all(bind=engine)
    _run_migrations()

