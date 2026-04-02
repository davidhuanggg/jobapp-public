"""
Integration tests: verify that YoE-based filtering correctly excludes job
postings whose experience requirements exceed the candidate's actual years.

These tests exercise the same pipeline used in find_matching_jobs:
  1. extract_min_yoe — pulls the required YoE from a description
  2. yoe_compatible  — compares it against the candidate's YoE
"""
import pytest
from app.services.experience_level_service import extract_min_yoe, yoe_compatible


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _job(title: str, description: str = "") -> dict:
    """Minimal job dict that mirrors what find_matching_jobs works with."""
    return {"title": title, "description_snippet": description}


def _apply_yoe_filter(jobs: list[dict], candidate_yoe: float | None) -> list[dict]:
    """
    Mirror of the YoE filter loop inside find_matching_jobs.
    """
    return [
        j for j in jobs
        if yoe_compatible(
            candidate_yoe,
            j.get("description_snippet") or "",
            j.get("title") or "",
        )
    ]


# ---------------------------------------------------------------------------
# 0 years of experience (fresh candidate)
# ---------------------------------------------------------------------------
class TestZeroYoECandidate:
    YOE = 0.0

    def test_no_requirement_is_included(self):
        jobs = [_job("Software Engineer", "Build cool products.")]
        assert len(_apply_yoe_filter(jobs, self.YOE)) == 1

    def test_entry_one_year_is_excluded(self):
        jobs = [_job("Software Engineer", "1+ years of experience required")]
        assert len(_apply_yoe_filter(jobs, self.YOE)) == 0

    def test_mid_two_years_is_excluded(self):
        jobs = [_job("Software Engineer", "2+ years of experience required")]
        assert len(_apply_yoe_filter(jobs, self.YOE)) == 0

    def test_senior_five_years_is_excluded(self):
        jobs = [_job("Software Engineer", "Minimum 5 years of experience")]
        assert len(_apply_yoe_filter(jobs, self.YOE)) == 0

    def test_senior_yoe_abbreviation_is_excluded(self):
        jobs = [_job("Software Engineer", "5+ yoe required")]
        assert len(_apply_yoe_filter(jobs, self.YOE)) == 0

    def test_mixed_batch(self):
        jobs = [
            _job("Junior Backend Engineer"),                              # no requirement → keep
            _job("Backend Engineer", "2+ years of experience"),           # 2 yoe → drop
            _job("Senior Backend Engineer", "5+ years of experience"),    # 5 yoe → drop
            _job("Backend Engineer", "Build APIs."),                      # no requirement → keep
            _job("Backend Engineer", "Minimum 6 years of experience"),    # 6 yoe → drop
        ]
        result = _apply_yoe_filter(jobs, self.YOE)
        assert len(result) == 2
        kept_titles = [j["title"] for j in result]
        assert "Junior Backend Engineer" in kept_titles
        assert "Backend Engineer" in kept_titles


# ---------------------------------------------------------------------------
# 2 years of experience
# ---------------------------------------------------------------------------
class TestTwoYoECandidate:
    YOE = 2.0

    def test_two_year_requirement_passes(self):
        jobs = [_job("Software Engineer", "2+ years of experience required")]
        assert len(_apply_yoe_filter(jobs, self.YOE)) == 1

    def test_one_year_requirement_passes(self):
        jobs = [_job("Software Engineer", "1+ years of experience")]
        assert len(_apply_yoe_filter(jobs, self.YOE)) == 1

    def test_three_year_requirement_is_excluded(self):
        jobs = [_job("Software Engineer", "3+ years of experience required")]
        assert len(_apply_yoe_filter(jobs, self.YOE)) == 0

    def test_five_year_requirement_is_excluded(self):
        jobs = [_job("Software Engineer", "5+ years of experience")]
        assert len(_apply_yoe_filter(jobs, self.YOE)) == 0

    def test_no_requirement_passes(self):
        jobs = [_job("Software Engineer", "Great opportunity.")]
        assert len(_apply_yoe_filter(jobs, self.YOE)) == 1


# ---------------------------------------------------------------------------
# 5 years of experience
# ---------------------------------------------------------------------------
class TestFiveYoECandidate:
    YOE = 5.0

    def test_five_year_requirement_passes(self):
        jobs = [_job("Senior Engineer", "5+ years of experience")]
        assert len(_apply_yoe_filter(jobs, self.YOE)) == 1

    def test_three_year_requirement_passes(self):
        jobs = [_job("Engineer", "3+ years of experience")]
        assert len(_apply_yoe_filter(jobs, self.YOE)) == 1

    def test_seven_year_requirement_is_excluded(self):
        jobs = [_job("Staff Engineer", "7+ years of experience")]
        assert len(_apply_yoe_filter(jobs, self.YOE)) == 0


# ---------------------------------------------------------------------------
# Unknown candidate YoE (None) — all jobs pass through
# ---------------------------------------------------------------------------
class TestUnknownYoECandidate:
    def test_all_jobs_pass(self):
        jobs = [
            _job("Intern"),
            _job("Junior Engineer"),
            _job("Engineer", "3+ years of experience"),
            _job("Senior Engineer", "5+ years of experience"),
        ]
        assert len(_apply_yoe_filter(jobs, None)) == 4
