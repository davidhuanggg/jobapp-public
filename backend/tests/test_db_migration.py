"""
Tests for the additive DB migration (_run_migrations).

Uses an in-memory SQLite database so no files are written and tests are isolated.
"""
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.db.database import _run_migrations, _MIGRATIONS
from app.db.models import Base, ResumeDB


@pytest.fixture()
def mem_engine():
    """Fresh in-memory SQLite engine with the base schema created."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture()
def legacy_engine():
    """
    Simulates an engine whose 'resumes' table predates the new columns —
    only the original columns exist.
    """
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE TABLE resumes ("
            "  id INTEGER PRIMARY KEY,"
            "  name VARCHAR,"
            "  email VARCHAR,"
            "  phone VARCHAR,"
            "  raw_text TEXT NOT NULL,"
            "  skills JSON,"
            "  content_hash VARCHAR(64) UNIQUE NOT NULL"
            ")"
        ))
        conn.commit()
    return engine


# ---------------------------------------------------------------------------
# Column existence after migration
# ---------------------------------------------------------------------------
class TestMigrationAddsColumns:
    def test_new_columns_present_on_fresh_db(self, mem_engine):
        """create_all already applies the full schema — all columns must exist."""
        cols = {c["name"] for c in inspect(mem_engine).get_columns("resumes")}
        assert "years_of_experience" in cols
        assert "career_level" in cols
        assert "is_student" in cols

    def test_migration_adds_columns_to_legacy_db(self, legacy_engine):
        """Legacy DB without the 3 new columns gets them after _run_migrations."""
        cols_before = {c["name"] for c in inspect(legacy_engine).get_columns("resumes")}
        assert "years_of_experience" not in cols_before

        _run_migrations(engine=legacy_engine)

        cols_after = {c["name"] for c in inspect(legacy_engine).get_columns("resumes")}
        assert "years_of_experience" in cols_after
        assert "career_level" in cols_after
        assert "is_student" in cols_after

    def test_migration_is_idempotent(self, legacy_engine):
        """Running _run_migrations twice must not raise."""
        _run_migrations(engine=legacy_engine)
        _run_migrations(engine=legacy_engine)   # second run — should be silent
        cols = {c["name"] for c in inspect(legacy_engine).get_columns("resumes")}
        assert "years_of_experience" in cols


# ---------------------------------------------------------------------------
# Data integrity after migration
# ---------------------------------------------------------------------------
class TestMigrationDataIntegrity:
    def test_existing_rows_survive_migration(self, legacy_engine):
        """Pre-existing rows must not be lost or corrupted after the migration."""
        with legacy_engine.connect() as conn:
            conn.execute(text(
                "INSERT INTO resumes (name, raw_text, content_hash) "
                "VALUES ('Alice', 'some text', 'abc123')"
            ))
            conn.commit()

        _run_migrations(engine=legacy_engine)

        with legacy_engine.connect() as conn:
            rows = conn.execute(text("SELECT name FROM resumes")).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "Alice"

    def test_new_columns_default_to_null_for_old_rows(self, legacy_engine):
        """After migration, old rows have NULL for the new columns (no default set)."""
        with legacy_engine.connect() as conn:
            conn.execute(text(
                "INSERT INTO resumes (name, raw_text, content_hash) "
                "VALUES ('Bob', 'text', 'def456')"
            ))
            conn.commit()

        _run_migrations(engine=legacy_engine)

        with legacy_engine.connect() as conn:
            row = conn.execute(
                text("SELECT years_of_experience, career_level, is_student FROM resumes")
            ).fetchone()
        assert row[0] is None   # years_of_experience
        assert row[1] is None   # career_level
        # is_student DEFAULT 0 — SQLite may keep it NULL for pre-existing rows
        assert row[2] in (None, 0, False)


# ---------------------------------------------------------------------------
# ORM layer writes and reads the new fields
# ---------------------------------------------------------------------------
class TestResumeDBNewFields:
    def test_orm_write_and_read_career_fields(self, mem_engine):
        Session = sessionmaker(bind=mem_engine)
        session = Session()

        resume = ResumeDB(
            raw_text="raw",
            content_hash="unique_hash_001",
            skills=[],
            years_of_experience=1.5,
            career_level="entry",
            is_student=False,
        )
        session.add(resume)
        session.commit()

        fetched = session.query(ResumeDB).filter_by(content_hash="unique_hash_001").first()
        assert fetched is not None
        assert fetched.years_of_experience == 1.5
        assert fetched.career_level == "entry"
        assert fetched.is_student is False
        session.close()

    def test_orm_student_intern(self, mem_engine):
        Session = sessionmaker(bind=mem_engine)
        session = Session()

        resume = ResumeDB(
            raw_text="student resume",
            content_hash="unique_hash_002",
            skills=[],
            years_of_experience=0.0,
            career_level="intern",
            is_student=True,
        )
        session.add(resume)
        session.commit()

        fetched = session.query(ResumeDB).filter_by(content_hash="unique_hash_002").first()
        assert fetched.career_level == "intern"
        assert fetched.is_student is True
        session.close()
