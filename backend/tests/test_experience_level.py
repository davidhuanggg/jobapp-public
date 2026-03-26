"""
Tests for experience_level_service — job-level inference and candidate compatibility.
"""
import pytest
from app.services.experience_level_service import (
    infer_job_level,
    level_compatible,
    LEVEL_ORDER,
)


# ---------------------------------------------------------------------------
# infer_job_level — title keywords
# ---------------------------------------------------------------------------
class TestInferJobLevelTitleKeywords:
    def test_senior_title(self):
        level, yoe = infer_job_level("", "Senior Backend Engineer")
        assert level == "senior"
        assert yoe is None

    def test_intern_title(self):
        level, _ = infer_job_level("", "Software Engineering Intern")
        assert level == "intern"

    def test_internship_title(self):
        level, _ = infer_job_level("", "Data Science Internship")
        assert level == "intern"

    def test_junior_title(self):
        level, _ = infer_job_level("", "Junior Frontend Developer")
        assert level == "entry"

    def test_entry_level_title(self):
        level, _ = infer_job_level("", "Entry-Level Software Engineer")
        assert level == "entry"

    def test_apprentice_title(self):
        level, _ = infer_job_level("", "Apprentice Developer")
        assert level == "apprenticeship"

    def test_mid_level_title(self):
        level, _ = infer_job_level("", "Mid-Level Data Analyst")
        assert level == "mid"

    def test_no_signal(self):
        level, yoe = infer_job_level("", "Software Engineer")
        assert level is None
        assert yoe is None


# ---------------------------------------------------------------------------
# infer_job_level — YoE from description
# ---------------------------------------------------------------------------
class TestInferJobLevelYoE:
    def test_entry_from_yoe(self):
        level, yoe = infer_job_level("Requires 1+ years of experience", "Software Engineer")
        assert level == "entry"
        assert yoe == 1.0

    def test_mid_from_yoe(self):
        level, yoe = infer_job_level("2+ years of experience required", "Engineer")
        assert level == "mid"
        assert yoe == 2.0

    def test_senior_from_yoe(self):
        level, yoe = infer_job_level("Minimum 5 years of experience", "")
        assert level == "senior"
        assert yoe == 5.0

    def test_picks_minimum_yoe(self):
        # "3+ years preferred, 5+ years ideal" — should pick 3
        level, yoe = infer_job_level("3+ years preferred, 5+ years ideal", "")
        assert yoe == 3.0
        assert level == "mid"

    def test_description_keyword_fallback(self):
        level, yoe = infer_job_level("Great opportunity for new grad candidates", "Developer")
        assert level == "entry"
        assert yoe is None


# ---------------------------------------------------------------------------
# level_compatible
# ---------------------------------------------------------------------------
class TestLevelCompatible:
    @pytest.mark.parametrize("candidate,job,expected", [
        # --- Active filter levels (apprenticeship / intern / entry) ---
        ("intern",   "intern",   True),
        ("entry",    "entry",    True),
        ("intern",   "entry",    True),   # one step up → compatible
        ("entry",    "mid",      True),   # one step up → compatible
        ("entry",    "intern",   True),   # one step down → compatible
        ("intern",   "mid",      False),  # two steps up → incompatible
        ("intern",   "senior",   False),  # three steps up → incompatible
        ("entry",    "senior",   False),  # two steps up → incompatible
        # --- Mid / senior bypass filtering entirely (not yet active) ---
        ("mid",      "mid",      True),
        ("mid",      "senior",   True),
        ("mid",      "entry",    True),
        ("mid",      "intern",   True),   # would be incompatible once active
        ("senior",   "senior",   True),
        ("senior",   "entry",    True),
        ("senior",   "intern",   True),   # would be incompatible once active
    ])
    def test_compatibility(self, candidate, job, expected):
        assert level_compatible(candidate, job) == expected

    def test_none_candidate_always_compatible(self):
        for level in LEVEL_ORDER:
            assert level_compatible(None, level) is True

    def test_none_job_defaults_to_mid(self):
        # Unknown job level is treated as "mid" (rank 3).
        # entry (2) vs mid (3): diff=1 → compatible
        assert level_compatible("entry", None) is True
        # intern (1) vs mid (3): diff=2 → incompatible
        assert level_compatible("intern", None) is False
        # apprenticeship (0) vs mid (3): diff=3 → incompatible
        assert level_compatible("apprenticeship", None) is False
        # mid (3) vs mid (3): diff=0 → compatible
        assert level_compatible("mid", None) is True
        # senior (4) vs mid (3): diff=1 → compatible
        assert level_compatible("senior", None) is True

    def test_both_none(self):
        assert level_compatible(None, None) is True

    def test_unknown_level_strings(self):
        # Unknown candidate level is not in _ACTIVE_FILTER_LEVELS → bypass filter.
        assert level_compatible("wizard", "mid") is True
        assert level_compatible("wizard", "senior") is True
